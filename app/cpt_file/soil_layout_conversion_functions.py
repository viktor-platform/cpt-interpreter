"""Copyright (c) 2022 VIKTOR B.V.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

VIKTOR B.V. PROVIDES THIS SOFTWARE ON AN "AS IS" BASIS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from copy import deepcopy
from io import BytesIO, StringIO
from math import ceil
from typing import List, Union

from munch import Munch, unmunchify
from viktor import Color, UserError
from viktor.geo import (
    GEFClassificationError,
    GEFFile,
    GEFParsingException,
    RobertsonMethod,
    Soil,
    SoilLayer,
    SoilLayout,
    TableMethod,
)

from .constants import ADDITIONAL_COLUMNS, DEFAULT_MIN_LAYER_THICKNESS


def convert_soil_layout_from_mm_to_meter(soil_layout: SoilLayout) -> SoilLayout:
    """Converts the units of the SoilLayout from mm to m."""
    serialization_dict = soil_layout.serialize()
    for layer in serialization_dict["layers"]:
        layer["top_of_layer"] = layer["top_of_layer"] / 1000
        layer["bottom_of_layer"] = layer["bottom_of_layer"] / 1000
    return SoilLayout.from_dict(serialization_dict)


def convert_soil_layout_from_meter_to_mm(soil_layout: SoilLayout) -> SoilLayout:
    """Converts the units of the SoilLayout from m to mm."""
    serialization_dict = soil_layout.serialize()
    for layer in serialization_dict["layers"]:
        layer["top_of_layer"] = layer["top_of_layer"] * 1000
        layer["bottom_of_layer"] = layer["bottom_of_layer"] * 1000
    return SoilLayout.from_dict(serialization_dict)


def filter_nones_from_params_dict(raw_dict) -> dict:
    """Removes all rows which contain one or more None-values"""
    rows_to_be_removed = []
    for row_index, items in enumerate(zip(*raw_dict["measurement_data"].values())):
        if None in items:
            rows_to_be_removed.append(row_index)
    for row in reversed(rows_to_be_removed):
        for signal in raw_dict["measurement_data"].keys():
            del raw_dict["measurement_data"][signal][row]
    return raw_dict


def convert_input_table_field_to_soil_layout(
    bottom_of_soil_layout_user: float,
    soil_layers_from_table_input: List[dict],
    soils: dict,
) -> SoilLayout:
    """Creates a SoilLayout from the user input.

    :param bottom_of_soil_layout_user: Bottom of soil layout in [m]
    :param soil_layers_from_table_input: Table where a row represents a layer.
    Each row should contain a soil name and top of layer [m].
    :param soils: Dictionary with soil names and their respective Soil.
    :return: SoilLayout
    """
    bottom = bottom_of_soil_layout_user
    soil_layers = []
    for layer in reversed(soil_layers_from_table_input):
        soil_name = layer["name"]
        top_of_layer = layer["top_of_layer"]
        try:
            soil_layers.append(SoilLayer(soils[soil_name], top_of_layer, bottom))
        except KeyError:
            raise UserError(
                f"'{soil_name}' is not available in the selected classification table.\n"
                f"Please select a different table, or reclassify the CPT files"
            )
        bottom = top_of_layer  # Set bottom of next soil layer to top of current layer.
    return convert_soil_layout_from_meter_to_mm(SoilLayout(soil_layers[::-1]))


def convert_soil_layout_to_input_table_field(soil_layout: SoilLayout) -> List[dict]:
    """Converts a SoilLayout to the parametrisation representation (Field = InputTable)."""
    return [
        {"name": layer.soil.properties.ui_name, "top_of_layer": layer.top_of_layer} for layer in soil_layout.layers
    ]


def convert_to_color(rgb: Union[str, tuple]) -> Color:
    """Simple conversion function that always returns a Color object"""
    if isinstance(rgb, tuple):
        return Color(*rgb)
    return Color(*[int(element) for element in rgb.strip().split(",")])


def get_water_level(cpt_data_object) -> float:
    """Water level is assigned to the value parsed from GEF file if it exists, otherwise a default is assigned to 1m
    below the surface level"""
    if hasattr(cpt_data_object, "water_level"):
        water_level = cpt_data_object.water_level
    else:
        water_level = cpt_data_object.ground_level_wrt_reference / 1e3 - 1
    return water_level


def _update_classification_table(classification_table: List[dict]) -> List[dict]:
    """Updates the table so that the min and max parameters for gamma are defined."""
    for row in classification_table:
        row["gamma_dry_min"] = None
        row["gamma_dry_max"] = row["gamma_dry"]
        row["gamma_wet_min"] = None
        row["gamma_wet_max"] = row["gamma_wet"]
        row["ui_name"] = row["name"]
    return classification_table


def _update_color_string(classification_table: List[dict]) -> List[dict]:
    """Converts the RGB color strings in the table into a tuple (R, G, B)"""
    for row in classification_table:
        if not isinstance(row["color"], Color):
            row["color"] = convert_to_color(row["color"])
    return classification_table


class Classification:
    """This class handles all logic related to selecting the correct method and table for classification of CPTData.

    It also provides the correct soil mapping needs for the visualizations of the soil layers.
    """

    def __init__(self, classification_params: Munch):
        self._method = classification_params.method
        self._table = unmunchify(classification_params.get(self._method))

    @property
    def table(self) -> List[dict]:
        """Returns a cleaned up table that can be used for the Classification methods"""
        if self._method == "robertson":
            return _update_color_string(self._table)
        return _update_classification_table(self._table)

    def method(self, ground_water_level) -> Union[TableMethod, RobertsonMethod]:
        """Returns the appropriate _ClassificationMethod for the CPTData.classify() function"""
        if self._method == "robertson":
            return RobertsonMethod(self.table)
        if self._method == "table":
            return TableMethod(self.table, ground_water_level=ground_water_level)
        raise UserError(f"The {self._method} method has not yet been implemented")

    def get_table_plot(self, gwl: float = 0, file_format: str = "pdf") -> Union[BytesIO, StringIO]:
        """Returns a plot of the selected _ClassificationMethod
        The ground water level is irrelevant for qualification plot and therefore set to zero
        to make sure the qualification plot is always downloadable."""
        if self._method == "robertson":
            raise TypeError
        if self._method == "table":
            return self.method(gwl).get_qualification_table_plot(fileformat=file_format)
        raise UserError(f"The {self._method} method has not yet been implemented")

    def get_table_plot_svg(self, gwl: float = 0, file_format: str = "svg") -> Union[BytesIO, StringIO]:
        """Returns a plot of the selected _ClassificationMethod"""
        if self._method == "robertson":
            raise TypeError
        if self._method == "table":
            return self.method(gwl).get_qualification_table_plot(fileformat=file_format)
        raise UserError(f"The {self._method} method has not yet been implemented")

    @property
    def soil_mapping(self) -> dict:
        """Returns a mapping between the soil name visible in the UI and the Soil object used in the logic"""
        soil_mapping = {}
        for soil in self.table:
            ui_name = soil["ui_name"]
            properties = deepcopy(soil)
            if self._method == "robertson":
                del properties["color"]
            soil_mapping[ui_name] = Soil(soil["name"], convert_to_color(soil["color"]), properties=properties)
        return soil_mapping

    def classify_cpt_file(self, cpt_file: GEFFile, saved_ground_water_level=None) -> dict:
        """Classify an uploaded CPT File based on the selected _ClassificationMethod"""

        try:
            # Parse the GEF file content
            cpt_data_object = cpt_file.parse(additional_columns=ADDITIONAL_COLUMNS, return_gef_data_obj=True)

            # Get the water level from user input, or calculate it from GEF
            if saved_ground_water_level is not None:
                ground_water_level = saved_ground_water_level
            else:
                ground_water_level = get_water_level(cpt_data_object)

            # Classify the CPTData object to get a SoilLayout
            soil_layout_obj = cpt_data_object.classify(
                method=self.method(ground_water_level), return_soil_layout_obj=True
            )

        except GEFParsingException as e:
            raise UserError(f"CPT Parsing: {str(e)}")
        except GEFClassificationError as e:
            raise UserError(f"CPT Classification: {str(e)}")

        soil_layout_filtered = soil_layout_obj.filter_layers_on_thickness(
            min_layer_thickness=DEFAULT_MIN_LAYER_THICKNESS,
            merge_adjacent_same_soil_layers=True,
        )
        soil_layout_filtered_in_m = convert_soil_layout_from_mm_to_meter(soil_layout_filtered)

        # Serialize the parsed CPT File content and update it with the new soil layout
        cpt_dict = cpt_data_object.serialize()
        cpt_dict["soil_layout_original"] = soil_layout_obj.serialize()
        cpt_dict["bottom_of_soil_layout_user"] = ceil(soil_layout_obj.bottom) / 1e3
        cpt_dict["soil_layout"] = convert_soil_layout_to_input_table_field(soil_layout_filtered_in_m)
        cpt_dict["ground_water_level"] = ground_water_level
        cpt_dict["x_rd"] = cpt_dict["headers"]["x_y_coordinates"][0] if "x_y_coordinates" in cpt_dict["headers"] else 0
        cpt_dict["y_rd"] = cpt_dict["headers"]["x_y_coordinates"][1] if "x_y_coordinates" in cpt_dict["headers"] else 0
        cpt_dict["gef"] = {"cpt_data": {"min_layer_thicknes": DEFAULT_MIN_LAYER_THICKNESS}}
        return cpt_dict
