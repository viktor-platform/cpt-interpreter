# pylint:disable=line-too-long                                 # Allows for longer line length inside a Parametrization
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
from typing import List

from viktor.parametrization import HiddenField
from viktor.parametrization import LineBreak
from viktor.parametrization import NumberField
from viktor.parametrization import OptionField
from viktor.parametrization import OptionListElement
from viktor.parametrization import Parametrization
from viktor.parametrization import Section
from viktor.parametrization import SetParamsButton
from viktor.parametrization import Tab
from viktor.parametrization import TableInput
from .constants import DEFAULT_MIN_LAYER_THICKNESS
from .constants import DEFAULT_ROBERTSON_TABLE


def _get_soils_options(**kwargs) -> List[OptionListElement]:
    """Options all possible soil type from the Classification parameter in the Project entity."""
    return [OptionListElement(soil.get('ui_name')) for soil in DEFAULT_ROBERTSON_TABLE]


class CPTFileParametrization(Parametrization):
    """Defines the input fields in left-side of the web UI in the CPT_file entity (Editor)."""
    gef = Tab('GEF')
    gef.cpt_data = Section('Properties and soil layout')

    gef.cpt_data.min_layer_thickness = NumberField('Minimum Layer Thickness', suffix='mm', min=0, step=50,
                                                   default=DEFAULT_MIN_LAYER_THICKNESS)
    gef.cpt_data.lb1 = LineBreak()
    gef.cpt_data.reset_original_layers = SetParamsButton('Original Soil Layout', method='reset_soil_layout_user')
    gef.cpt_data.filter_thin_layers = SetParamsButton('Filter Layer Thickness',
                                                      method='filter_soil_layout_on_min_layer_thickness')
    gef.cpt_data.lb2 = LineBreak()
    gef.cpt_data.soil_layout = TableInput('Soil layout', name='soil_layout')
    gef.cpt_data.soil_layout.name = OptionField("Material", options=_get_soils_options)
    gef.cpt_data.soil_layout.top_of_layer = NumberField("Top NAP [m]", num_decimals=1)

    gef.cpt_data.gef_headers = HiddenField('GEF Headers', name='headers')
    gef.cpt_data.bottom_of_soil_layout_user = HiddenField('GEF Soil bottom', name='bottom_of_soil_layout_user')
    gef.cpt_data.ground_water_level = HiddenField('Phreatic level', name='ground_water_level')
    gef.cpt_data.measurement_data = HiddenField('GEF Measurement data', name='measurement_data')
    gef.cpt_data.soil_layout_original = HiddenField('Soil layout original', name='soil_layout_original')
