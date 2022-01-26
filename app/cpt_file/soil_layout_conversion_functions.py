from copy import deepcopy
from io import BytesIO
from io import StringIO
from math import ceil
from typing import List
from typing import Union

from munch import Munch
from munch import unmunchify
from viktor import Color
from viktor import UserException
from viktor.api_v1 import API
from viktor.geo import GEFClassificationError
from viktor.geo import GEFParsingException
from viktor.geo import PiezoLine
from viktor.geo import RobertsonMethod
from viktor.geo import Soil
from viktor.geo import SoilLayer
from viktor.geo import SoilLayer2D
from viktor.geo import SoilLayout
from viktor.geo import TableMethod
from viktor.geometry import Point
from viktor.geometry import Polyline as PolylineSDK
from viktor.utils import memoize

from .constants import ADDITIONAL_COLUMNS
from .constants import DEFAULT_MIN_LAYER_THICKNESS
from .cpt.gef_file import GEFFile
from .cpt.imbro_file import IMBROFile


def convert_soil_layout_from_mm_to_m(soil_layout: SoilLayout) -> SoilLayout:
    """Converts the units of the SoilLayout from mm to m."""
    serialization_dict = soil_layout.serialize()
    for layer in serialization_dict["layers"]:
        layer["top_of_layer"] = layer["top_of_layer"] / 1000
        layer["bottom_of_layer"] = layer["bottom_of_layer"] / 1000
    return SoilLayout.from_dict(serialization_dict)


def convert_soil_layout_from_m_to_mm(soil_layout: SoilLayout) -> SoilLayout:
    """Converts the units of the SoilLayout from m to mm."""
    serialization_dict = soil_layout.serialize()
    for layer in serialization_dict["layers"]:
        layer["top_of_layer"] = layer["top_of_layer"] * 1000
        layer["bottom_of_layer"] = layer["bottom_of_layer"] * 1000
    return SoilLayout.from_dict(serialization_dict)


def convert_input_table_field_to_soil_layout(bottom_of_soil_layout_user: float,
                                             soil_layers_from_table_input: List[dict],
                                             soils: dict) -> SoilLayout:
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
            raise UserException(f"{soil_name} is not available in the selected classification table.\n"
                                f"Please select a different table, or reclassify the CPT files")
        bottom = top_of_layer  # Set bottom of next soil layer to top of current layer.
    return convert_soil_layout_from_m_to_mm(SoilLayout(soil_layers[::-1]))


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


def _update_classification_table(classification_table: List[dict]) -> List[dict]:
    """Updates the table so that the min and max parameters for gamma are defined."""
    for row in classification_table:
        row['gamma_dry_min'] = None
        row['gamma_dry_max'] = row['gamma_dry']
        row['gamma_wet_min'] = None
        row['gamma_wet_max'] = row['gamma_wet']
        row['ui_name'] = row['name']
    return classification_table


def _update_color_string(classification_table: List[dict]) -> List[dict]:
    """Converts the RGB color strings in the table into a tuple (R, G, B)"""
    for row in classification_table:
        if not isinstance(row['color'], Color):
            row['color'] = convert_to_color(row['color'])
    return classification_table


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
        if self._method == 'robertson':
            return _update_color_string(self._table)
        return _update_classification_table(self._table)

    def method(self, ground_water_level) -> Union[TableMethod, RobertsonMethod]:
        """Returns the appropriate _ClassificationMethod for the CPTData.classify() function"""
        if self._method == 'robertson':
            return RobertsonMethod(self.table)
        if self._method == 'table':
            return TableMethod(self.table, ground_water_level=ground_water_level)
        raise UserException(f'The {self._method} method has not yet been implemented')

    def get_table_plot(self, gwl: float = 0, file_format: str = 'pdf') -> Union[BytesIO, StringIO]:
        """Returns a plot of the selected _ClassificationMethod
        The ground water level is irrelevant for qualification plot and therefore set to zero
        to make sure the qualification plot is always downloadable."""
        if self._method == 'robertson':
            raise TypeError
        if self._method == 'table':
            return self.method(gwl).get_qualification_table_plot(fileformat=file_format)
        raise UserException(f'The {self._method} method has not yet been implemented')

    def get_table_plot_svg(self, gwl: float = 0, file_format: str = 'svg') -> Union[BytesIO, StringIO]:
        """Returns a plot of the selected _ClassificationMethod"""
        if self._method == 'robertson':
            raise TypeError
        if self._method == 'table':
            return self.method(gwl).get_qualification_table_plot(fileformat=file_format)
        raise UserException(f'The {self._method} method has not yet been implemented')

    @property
    def soil_mapping(self) -> dict:
        """Returns a mapping between the soil name visible in the UI and the Soil object used in the logic"""
        soil_mapping = {}
        for soil in self.table:
            ui_name = soil['ui_name']
            properties = deepcopy(soil)
            if self._method == 'robertson':
                del properties['color']
            soil_mapping[ui_name] = Soil(soil['name'], convert_to_color(soil['color']), properties=properties)
        return soil_mapping

    def classify_cpt_file(self, cpt_file: Union[GEFFile, IMBROFile], saved_ground_water_level=None) -> dict:
        """Classify an uploaded CPT File based on the selected _ClassificationMethod"""

        try:
            # Parse the GEF file content
            cpt_data_object = cpt_file.parse(additional_columns=ADDITIONAL_COLUMNS, return_gef_data_obj=True)

            ground_water_level = get_water_level(cpt_data_object)

            # Classify the CPTData object to get a SoilLayout
            soil_layout_obj = cpt_data_object.classify(method=self.method(ground_water_level),
                                                       return_soil_layout_obj=True)

        except GEFParsingException as e:
            raise UserException(f"CPT Parsing: {str(e)}")
        except GEFClassificationError as e:
            raise UserException(f"CPT Classification: {str(e)}")

        # TODO: do we really want to apply a standard filtering whenever we classify a cpt file?
        soil_layout_filtered = soil_layout_obj.filter_layers_on_thickness(
            min_layer_thickness=DEFAULT_MIN_LAYER_THICKNESS, merge_adjacent_same_soil_layers=True)
        soil_layout_filtered_in_m = convert_soil_layout_from_mm_to_m(soil_layout_filtered)

        # Serialize the parsed CPT File content and update it with the new soil layout
        cpt_dict = cpt_data_object.serialize()
        cpt_dict['soil_layout_original'] = soil_layout_obj.serialize()
        cpt_dict['bottom_of_soil_layout_user'] = ceil(soil_layout_obj.bottom) / 1e3
        cpt_dict['soil_layout'] = convert_soil_layout_to_input_table_field(soil_layout_filtered_in_m)
        cpt_dict['ground_water_level'] = ground_water_level
        cpt_dict['x_rd'] = cpt_dict['headers']['x_y_coordinates'][0] if 'x_y_coordinates' in cpt_dict['headers'] else 0
        cpt_dict['y_rd'] = cpt_dict['headers']['x_y_coordinates'][1] if 'x_y_coordinates' in cpt_dict['headers'] else 0
        return cpt_dict


def convert_table_to_soil_layers_2d(soil_layout_table: List[dict], columns: List[str], bottoms: List[float],
                                    positions: List[float], soils: dict, phreatic_levels: List[float]):
    """Creates a list of PositionalSoilLayouts from the user input table."""
    if not soil_layout_table:
        raise UserException('The soil layout table is still empty')
    soil_layers_2d = []
    bottom_profile = [Point(position, bottom * 1e3) for position, bottom in zip(positions, bottoms)]

    r = soil_layout_table[0]
    pl_line_bottom = PiezoLine([Point(positions[0], bottoms[0] * 1e3),
                                Point(positions[-1], bottoms[-1] * 1e3)], phreatic=False)
    pl_line_top = PiezoLine([Point(positions[0], r[columns[0]] * 1e3 if r[columns[0]] else bottom_profile[0].y),
                             Point(positions[-1], r[columns[-1]] * 1e3 if r[columns[-1]] else bottom_profile[-1].y)],
                            phreatic=False)

    # Because the table only defines the top level of each layer, we iterate from bottom to top so we can re-use the
    # top-level of the previous layer as the new bottom-level of the current layer
    first_phreatic = True
    for row in soil_layout_table[::-1]:
        soil = soils[row['layer']]
        top_profile = [Point(position, row[column] * 1e3 if row[column] else bottom_profile[i].y)
                       for i, (position, column) in enumerate(zip(positions, columns))]

        if any(pt_bot.y <= phreatic_level * 1e3 <= pt_top.y
               for pt_top, pt_bot, phreatic_level in zip(top_profile, bottom_profile, phreatic_levels)):
            piezo_line = PiezoLine([Point(x, y) for x, y in [(positions[0], phreatic_levels[0] * 1e3),
                                                             (positions[-1], phreatic_levels[-1] * 1e3)]],
                                   phreatic=first_phreatic)

            first_phreatic = False
            soil_layers_2d.append(SoilLayer2D(soil, PolylineSDK(top_profile), PolylineSDK(bottom_profile),
                                              piezo_line_top=piezo_line))
        else:
            soil_layers_2d.append(SoilLayer2D(soil, PolylineSDK(top_profile), PolylineSDK(bottom_profile)))

        bottom_profile = top_profile

    soil_layers_2d[-1].piezo_line_top = pl_line_top
    soil_layers_2d[0].piezo_line_bottom = pl_line_bottom
    return soil_layers_2d


@memoize
def get_cpt_file_content(extension: str, file_name: str, entity_id: int) -> Union[str, bytes]:
    """Returns the file_content in a specific format (GEF or BRO XML)

    If uploaded file was IMBROFile and a GEF format is required, it converts the IMBROFile to a GEFFile.
    If uploaded file was GEF XML and a IMBRO format is required, it converts the GEFFile to a IMBROFile.

    Note that this call can be memoized, because it only uses the OldAPI to download from S3 (immutable, because the
    file content cannot be changed after upload)
    """
    file = API().get_entity_file(entity_id)
    if file_name.lower().endswith('gef'):
        file_content = file.getvalue(encoding='ISO-8859-1')
    else:
        file_content = file.getvalue_binary()

    if file_name.lower().endswith('gef') and extension.lower() == 'xml':
        file_content = GEFFile(file_content).convert_to_imbro_file_content()
    if file_name.lower().endswith('xml') and extension.lower() == 'gef':
        file_content = IMBROFile(file_content).convert_to_gef_file_content()
    return file_content
