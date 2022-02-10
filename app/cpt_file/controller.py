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
from munch import Munch
from munch import unmunchify

from viktor import File
from viktor import ParamsFromFile
from viktor import UserException
from viktor.core import ViktorController
from viktor.core import progress_message
from viktor.geo import GEFFile
from viktor.geo import SoilLayout
from viktor.result import SetParametersResult
from viktor.views import DataGroup
from viktor.views import DataItem
from viktor.views import WebAndDataResult
from viktor.views import WebAndDataView
from .constants import DEFAULT_ROBERTSON_TABLE
from .model import CPT
from .parametrization import CPTFileParametrization
from .soil_layout_conversion_functions import classify_cpt_file
from .soil_layout_conversion_functions import convert_input_table_field_to_soil_layout
from .soil_layout_conversion_functions import convert_soil_layout_from_mm_to_meter
from .soil_layout_conversion_functions import convert_soil_layout_to_input_table_field


class CPTFileController(ViktorController):
    """Controller class which acts as interface for the Sample entity type."""
    label = 'CPT File'
    parametrization = CPTFileParametrization
    viktor_convert_entity_field = True

    @ParamsFromFile(file_types=['.gef'])
    def process_file(self, file: File, **kwargs) -> dict:
        """Classify the CPT file when it is first uploaded"""
        cpt_file = GEFFile(file.getvalue("ISO-8859-1"))
        return classify_cpt_file(cpt_file)

    @WebAndDataView("GEF", duration_guess=3)
    def visualize(self, params: Munch, entity_id: int, **kwargs) -> WebAndDataResult:
        """Visualizes the Qc and Rf line plots, the soil layout bar plots and the data of the cpt."""
        cpt = CPT(cpt_params=params, soils=DEFAULT_ROBERTSON_TABLE, entity_id=entity_id)
        data_group = self.get_data_group(params)
        return WebAndDataResult(html=cpt.visualize(), data=data_group)

    @staticmethod
    def get_data_group(params: Munch) -> DataGroup:
        """Collect the necessary information from the GEF headers and return a DataGroup with the data"""
        headers = params.get('headers')
        if not headers:
            raise UserException('GEF file has no headers')
        try:
            x_coordinate, y_coordinate = params.x_rd, params.y_rd
        except AttributeError:
            x_coordinate, y_coordinate = headers.x_y_coordinates
        height_system = headers.height_system
        ground_level_wrt_ref_m = headers.ground_level_wrt_reference_m
        return DataGroup(
            ground_level_wrt_reference_m=DataItem('Ground level (NAP)', ground_level_wrt_ref_m or -999, suffix='m'),
            ground_water_level=DataItem('Phreatic level (NAP)', params.ground_water_level),
            height_system=DataItem('Height system', height_system or '-'),
            coordinates=DataItem('Coordinates', '', subgroup=DataGroup(
                x_coordinate=DataItem('X-coordinate', x_coordinate or 0, suffix='m'),
                y_coordinate=DataItem('Y-coordinate', y_coordinate or 0, suffix='m'),
            ))
        )

    @staticmethod
    def filter_soil_layout_on_min_layer_thickness(params: Munch, **kwargs) -> SetParametersResult:
        """Remove all user defined layers below the filter threshold."""
        progress_message('Filtering thin layers from soil layout')
        # Create SoilLayout and filter.
        bottom_of_soil_layout_user = params.get('bottom_of_soil_layout_user')
        soil_layout_user = convert_input_table_field_to_soil_layout(bottom_of_soil_layout_user,
                                                                    params.soil_layout)
        soil_layout_user.filter_layers_on_thickness(params.gef.cpt_data.min_layer_thickness,
                                                    merge_adjacent_same_soil_layers=True)
        soil_layout_user = convert_soil_layout_from_mm_to_meter(soil_layout_user)
        table_input_soil_layers = convert_soil_layout_to_input_table_field(soil_layout_user)

        return SetParametersResult({'soil_layout': table_input_soil_layers})

    @staticmethod
    def reset_soil_layout_user(params: Munch, **kwargs) -> SetParametersResult:
        """Place the original soil layout (after parsing) in the table input."""
        progress_message('Resetting soil layout to original unfiltered result')
        soil_layout_original = SoilLayout.from_dict(unmunchify(params.soil_layout_original))
        table_input_soil_layers = convert_soil_layout_to_input_table_field(
            convert_soil_layout_from_mm_to_meter(soil_layout_original)
        )
        return SetParametersResult(
            {'soil_layout': table_input_soil_layers,
             'bottom_of_soil_layout_user': params.get('bottom_of_soil_layout_user')}
        )
