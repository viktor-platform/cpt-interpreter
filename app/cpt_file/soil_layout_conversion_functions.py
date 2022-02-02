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
from math import ceil
from typing import List
from typing import Union

from viktor import Color
from viktor import UserException
from viktor.geo import GEFClassificationError
from viktor.geo import GEFFile
from viktor.geo import GEFParsingException
from viktor.geo import RobertsonMethod
from viktor.geo import Soil
from viktor.geo import SoilLayer
from viktor.geo import SoilLayout
from .constants import ADDITIONAL_COLUMNS
from .constants import DEFAULT_MIN_LAYER_THICKNESS
from .constants import DEFAULT_ROBERTSON_TABLE


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


def convert_input_table_field_to_soil_layout(bottom_of_soil_layout_user: float,
                                             soil_layers_from_table_input: List[dict]) -> SoilLayout:
    """Creates a SoilLayout from the user input.

    :param bottom_of_soil_layout_user: Bottom of soil layout in [m]
    :param soil_layers_from_table_input: Table where a row represents a layer.
    Each row should contain a soil name and top of layer [m].
    :return: SoilLayout
    """
    bottom = bottom_of_soil_layout_user
    soils = get_soil_mapping()
    soil_layers = []
    for layer in reversed(soil_layers_from_table_input):
        soil_name = layer["name"]
        top_of_layer = layer["top_of_layer"]
        try:
            soil_layers.append(SoilLayer(soils[soil_name], top_of_layer, bottom))
        except KeyError as soil_name_no_exist:
            raise UserException(f"{soil_name} is not available in the selected classification " f"table.\n "
                                f"Please select a different table, or reclassify the CPT files") from soil_name_no_exist
        bottom = top_of_layer  # Set bottom of next soil layer to top of current layer.
    return convert_soil_layout_from_meter_to_mm(SoilLayout(soil_layers[::-1]))


def convert_soil_layout_to_input_table_field(soil_layout: SoilLayout) -> List[dict]:
    """Converts a SoilLayout to the parametrisation representation (Field = InputTable).

    :param soil_layout: SoilLayout
    :return: List containing dictionaries for the InputTable. Structure:
    [
    {'name': 'Zand grof', 'top_of_layer': -5},
    {'name': 'Zand grof', 'top_of_layer': -8},
    ...
    ]
    """
    table_input_soil_layers = [
        {
            "name": layer.soil.properties.ui_name,
            "top_of_layer": layer.top_of_layer
        }
        for layer in soil_layout.layers
    ]

    return table_input_soil_layers


def convert_to_color(rgb: Union[str, tuple]) -> Color:
    """Simple conversion function that always returns a Color object"""
    if isinstance(rgb, tuple):
        return Color(*rgb)
    return Color(*[int(element) for element in rgb.strip().split(',')])


def get_water_level(cpt_data_object) -> float:
    """Water level is assigned to the value parsed from GEF file if it exists, otherwise a default is assigned to 1m
    below the surface level"""
    if hasattr(cpt_data_object, 'water_level'):
        water_level = cpt_data_object.water_level
    else:
        water_level = cpt_data_object.ground_level_wrt_reference/1e3 - 1
    return water_level


def get_soil_mapping() -> dict:
    """Returns a mapping between the soil name visible in the UI and the Soil object used in the logic"""
    soil_mapping = {}
    for soil in DEFAULT_ROBERTSON_TABLE:
        ui_name = soil['ui_name']
        properties = deepcopy(soil)
        del properties['color']
        soil_mapping[ui_name] = Soil(soil['name'], convert_to_color(soil['color']), properties=properties)
    return soil_mapping


def classify_cpt_file(cpt_file: GEFFile) -> dict:
    """Classify an uploaded CPT File based on the selected _ClassificationMethod"""

    try:
        # Parse the GEF file content
        cpt_data_object = cpt_file.parse(additional_columns=ADDITIONAL_COLUMNS, return_gef_data_obj=True)

        ground_water_level = get_water_level(cpt_data_object)

        # Classify the CPTData object to get a SoilLayout
        soil_layout_obj = cpt_data_object.classify(method=RobertsonMethod(DEFAULT_ROBERTSON_TABLE),
                                                   return_soil_layout_obj=True)

    except GEFParsingException as parsing_exception:
        raise UserException(f"CPT Parsing: {str(parsing_exception)}") from parsing_exception
    except GEFClassificationError as classification_exception:
        raise UserException(f"CPT Classification: {str(classification_exception)}") from classification_exception

    soil_layout_filtered = soil_layout_obj.filter_layers_on_thickness(
        min_layer_thickness=DEFAULT_MIN_LAYER_THICKNESS, merge_adjacent_same_soil_layers=True)
    soil_layout_filtered_in_m = convert_soil_layout_from_mm_to_meter(soil_layout_filtered)

    # Serialize the parsed CPT File content and update it with the new soil layout
    cpt_dict = cpt_data_object.serialize()
    cpt_dict['soil_layout_original'] = soil_layout_obj.serialize()
    cpt_dict['bottom_of_soil_layout_user'] = ceil(soil_layout_obj.bottom) / 1e3
    cpt_dict['soil_layout'] = convert_soil_layout_to_input_table_field(soil_layout_filtered_in_m)
    cpt_dict['ground_water_level'] = ground_water_level
    cpt_dict['x_rd'] = cpt_dict['headers']['x_y_coordinates'][0] if 'x_y_coordinates' in cpt_dict['headers'] else 0
    cpt_dict['y_rd'] = cpt_dict['headers']['x_y_coordinates'][1] if 'x_y_coordinates' in cpt_dict['headers'] else 0
    return cpt_dict
