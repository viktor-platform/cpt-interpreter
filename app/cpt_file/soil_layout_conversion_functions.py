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
    """Creates a SoilLayout from the user input."""
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
    """Converts a SoilLayout to the parametrisation representation (Field = InputTable)."""
    return [
        {
            "name": layer.soil.properties.ui_name,
            "top_of_layer": layer.top_of_layer
        }
        for layer in soil_layout.layers
    ]


def get_soil_mapping() -> dict:
    """Returns a mapping between the soil name visible in the UI and the Soil object used in the logic"""
    soil_mapping = {}
    for soil in DEFAULT_ROBERTSON_TABLE:
        # remove soil color from the properties
        properties = deepcopy(soil)
        del properties['color']

        # create soil mapping
        soil_mapping[soil['ui_name']] = Soil(soil['name'], Color(*soil['color']), properties=properties)
    return soil_mapping


def classify_cpt_file(cpt_file: GEFFile) -> dict:
    """Classify an uploaded CPT File based on the selected _ClassificationMethod"""

    try:
        # Parse the GEF file content
        cpt_data_object = cpt_file.parse(additional_columns=ADDITIONAL_COLUMNS, return_gef_data_obj=True)

        # Water level the value parsed from GEF file if it exists
        if hasattr(cpt_data_object, 'water_level'):
            ground_water_level = cpt_data_object.water_level
        else:  # a default is assigned (1m below the surface level)
            ground_water_level = round(cpt_data_object.ground_level_wrt_reference/1e3 - 1, 2)

        # Classify the CPTData object to get a SoilLayout
        soil_layout_obj = cpt_data_object.classify(method=RobertsonMethod(DEFAULT_ROBERTSON_TABLE),
                                                   return_soil_layout_obj=True)

    except GEFParsingException as parsing_exception:
        raise UserException(f"CPT Parsing: {str(parsing_exception)}") from parsing_exception
    except GEFClassificationError as classification_exception:
        raise UserException(f"CPT Classification: {str(classification_exception)}") from classification_exception

    # filter thickness and convert to meter
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
