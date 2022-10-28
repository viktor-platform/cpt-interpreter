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
from viktor.parametrization import Text
from viktor.parametrization import TableInput
from .constants import DEFAULT_MIN_LAYER_THICKNESS
from .constants import DEFAULT_ROBERTSON_TABLE


def _get_soils_options(**kwargs) -> List[OptionListElement]:
    """Options all possible soil type from the Classification parameter in the Project entity."""
    return [OptionListElement(soil.get('ui_name')) for soil in DEFAULT_ROBERTSON_TABLE]


class CPTFileParametrization(Parametrization):
    """Defines the input fields in left-side of the web UI in the CPT_file entity (Editor)."""
    gef = Tab('GEF')
    gef.text = Text("Use the table below to change the interpreted soil layout by changing the positions of the layers, "
                    "adding rows or changing the material type.")

    gef.filter_thin_layers = SetParamsButton('Filter Layer Thickness',
                                             method='filter_soil_layout_on_min_layer_thickness', flex=60,
                                             description="Filter the soil layout to remove layers that are "
                                                         "thinner than the minimum layer thickness")
    gef.min_layer_thickness = NumberField('Minimum Layer Thickness', suffix='mm', min=0, step=50,
                                          default=DEFAULT_MIN_LAYER_THICKNESS,
                                          flex=40)

    gef.reset_original_layers = SetParamsButton('Reset to original Soil Layout',
                                                method='reset_soil_layout_user',
                                                flex=100,
                                                description="Reset the table to the original soil layout" )

    gef.ground_water_level = NumberField('Phreatic level', name='ground_water_level', suffix='m NAP', flex=50)
    gef.ground_level = NumberField('Ground level', name='ground_level', suffix='m NAP', flex=50)
    gef.soil_layout = TableInput('Soil layout', name='soil_layout')
    gef.soil_layout.name = OptionField("Material", options=_get_soils_options)
    gef.soil_layout.top_of_layer = NumberField("Top (m NAP)", num_decimals=1)

    # hidden fields
    gef.gef_headers = HiddenField('GEF Headers', name='headers')
    gef.bottom_of_soil_layout_user = HiddenField('GEF Soil bottom', name='bottom_of_soil_layout_user')
    gef.measurement_data = HiddenField('GEF Measurement data', name='measurement_data')
    gef.soil_layout_original = HiddenField('Soil layout original', name='soil_layout_original')
