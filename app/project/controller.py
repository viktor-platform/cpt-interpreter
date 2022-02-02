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

from viktor.api_v1 import API
from viktor.core import ViktorController
from viktor.views import MapResult
from viktor.views import MapView
from .parametrization import ProjectParametrization
from ..cpt_file.constants import CPT_LEGEND
from ..cpt_file.model import CPT


class ProjectController(ViktorController):
    """Controller class which acts as interface for the Sample entity type."""
    label = "Sample"
    children = ['CPTFile']
    show_children_as = 'Table'
    parametrization = ProjectParametrization
    viktor_convert_entity_field = True

    @MapView('Map', duration_guess=2)
    def visualize_map(self, params: Munch, entity_id: int, **kwargs) -> MapResult:
        """Visualize the MapView with all CPT locations and a polyline"""

        all_cpt_models = self.get_cpt_models(entity_id)

        cpt_features = []
        for cpt in all_cpt_models:
            cpt_features.append(cpt.get_map_point())

        return MapResult([*cpt_features], [], CPT_LEGEND)

    @staticmethod
    def get_cpt_models(entity_id):
        """Obtains all child 'CPT File' entities"""
        cpt_file_entities = API().get_entity(entity_id).children(entity_type_names=['CPTFile'], include_params=True)
        all_cpt_files = [CPT(cpt_params=cpt_entity.last_saved_params, entity_id=cpt_entity.id)
                         for cpt_entity in cpt_file_entities]
        return all_cpt_files
