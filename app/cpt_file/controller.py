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
from viktor.api_v1 import API as NewAPI
from viktor.api_v1 import Entity
from viktor.core import ViktorController
from viktor.core import progress_message
from viktor.geo import SoilLayout
from viktor.result import SetParametersResult
from viktor.views import DataGroup
from viktor.views import DataItem
from viktor.views import DataResult
from viktor.views import DataView
from viktor.views import Summary
from viktor.views import SummaryItem
from viktor.views import WebResult
from viktor.views import WebView
from .cpt import GEFFile
from .model import CPT
from .parametrization import CPTFileParametrization
from .soil_layout_conversion_functions import Classification
from .soil_layout_conversion_functions import convert_input_table_field_to_soil_layout
from .soil_layout_conversion_functions import convert_soil_layout_from_mm_to_m
from .soil_layout_conversion_functions import convert_soil_layout_to_input_table_field


class CPTFileController(ViktorController):
    """Controller class which acts as interface for the Sample entity type."""
    label = 'CPT File'
    parametrization = CPTFileParametrization
    viktor_convert_entity_field = True

    model = CPT
    encoding = "ISO-8859-1"
    summary = Summary()

    @ParamsFromFile(file_types=['.gef'])
    def process_file(self, file: File, entity_id: int, **kwargs) -> dict:
        self.classify_file(file, entity_id=entity_id)
        return self.classify_file(file, entity_id=entity_id)

    @staticmethod
    def _get_project_entity(entity_id: int) -> Entity:
        """Retrieves the project entity through an API call"""
        return NewAPI().get_entity(entity_id).parent()

    def get_classification(self, entity_id: int) -> Classification:
        """Returns Classification object based on Project classification parameters"""
        project_params = self._get_project_entity(entity_id).last_saved_params
        return Classification(project_params.soil_interpretation.classification)

    def classify_file(self, file: File, entity_id: int) -> dict:
        """Classify the CPT file when it is first uploaded"""
        cpt_file = GEFFile(file.getvalue(self.encoding))
        classification = self.get_classification(entity_id)
        return classification.classify_cpt_file(cpt_file)

    @WebView("GEF", duration_guess=3)
    def visualize(self, params: Munch, entity_id: int, **kwargs) -> WebResult:
        """Visualizes the Qc and Rf line plots and also the soil layout bar plots"""
        classification = self.get_classification(entity_id)
        soils = classification.soil_mapping
        headers = params.get('headers')
        if not headers:
            raise UserException('GEF file has no headers')
        gef = self.model(cpt_params=params, soils=soils, entity_id=entity_id)
        return WebResult(html=gef.visualize())

    @DataView('Summary', duration_guess=1)
    def summarize(self, params: Munch, entity_id: int, **kwargs) -> DataResult:
        """Summarizes the data inside the GEF headers"""
        headers = params.get('headers')
        if not headers:
            raise UserException('GEF file has no headers')
        data = self._get_data_group(params)
        return DataResult(data)

    @staticmethod
    def _get_data_group(params: Munch) -> DataGroup:
        """Collect the necessary information from the GEF headers and return a DataGroup with the data"""
        height_system = ground_level_wrt_ref_m = None
        headers = params.get('headers')
        if headers:
            try:
                x, y = params.x_rd, params.y_rd
            except AttributeError:
                x, y = headers.x_y_coordinates
            height_system = headers.height_system
            ground_level_wrt_ref_m = headers.ground_level_wrt_reference_m
        return DataGroup(
            ground_level_wrt_reference_m=DataItem('Ground level (NAP)', ground_level_wrt_ref_m or -999, suffix='m'),
            height_system=DataItem('Height system', height_system or '-'),
            coordinates=DataItem('Coordinates', '', subgroup=DataGroup(
                x_coordinate=DataItem('X-coordinate', x or 0, suffix='m'),
                y_coordinate=DataItem('Y-coordinate', y or 0, suffix='m'),
            ))
        )

    def filter_soil_layout_on_min_layer_thickness(self, params: Munch, entity_id: int, **kwargs) -> SetParametersResult:
        """Remove all user defined layers below the filter threshold."""
        progress_message('Filtering thin layers from soil layout')
        soil_mapping = self.get_classification(entity_id).soil_mapping
        # Create SoilLayout and filter.
        soil_layout_user = convert_input_table_field_to_soil_layout(params.bottom_of_soil_layout_user,
                                                                    params.soil_layout,
                                                                    soil_mapping)
        soil_layout_user.filter_layers_on_thickness(params.gef.cpt_data.min_layer_thickness,
                                                    merge_adjacent_same_soil_layers=True)
        soil_layout_user = convert_soil_layout_from_mm_to_m(soil_layout_user)
        table_input_soil_layers = convert_soil_layout_to_input_table_field(soil_layout_user)

        return SetParametersResult({'soil_layout': table_input_soil_layers})

    def reset_soil_layout_user(self, params: Munch, **kwargs) -> SetParametersResult:
        """Place the original soil layout (after parsing) in the table input."""
        progress_message('Resetting soil layout to original unfiltered result')
        soil_layout_original = SoilLayout.from_dict(unmunchify(params.soil_layout_original))
        table_input_soil_layers = convert_soil_layout_to_input_table_field(
            convert_soil_layout_from_mm_to_m(soil_layout_original)
        )
        return SetParametersResult(
            {'soil_layout': table_input_soil_layers,
             'bottom_of_soil_layout_user': soil_layout_original.bottom / 1e3}
        )
