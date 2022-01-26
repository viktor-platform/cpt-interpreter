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

from app.cpt_file.constants import DEFAULT_MIN_LAYER_THICKNESS
from app.cpt_file.constants import DEFAULT_SOIL_NAMES
from viktor.api_v1 import API
from viktor.api_v1 import EntityList
from viktor.parametrization import And
from viktor.parametrization import DownloadButton
from viktor.parametrization import IsEqual
from viktor.parametrization import IsFalse
from viktor.parametrization import IsTrue
from viktor.parametrization import Lookup
from viktor.parametrization import NumberField
from viktor.parametrization import OptionField
from viktor.parametrization import OptionListElement
from viktor.parametrization import Parametrization
from viktor.parametrization import Section
from viktor.parametrization import SetParamsButton
from viktor.parametrization import Tab
from viktor.parametrization import TableInput
from viktor.parametrization import TextField
from viktor.parametrization import ToggleButton
#
# DEFAULT_ROBERTSON_TABLE = [
#     {
#         'name': 'Robertson zone unknown',
#         'ui_name': 'Onbekend materiaal',
#         'color': '255, 0, 0',
#         'gamma_dry': 0,
#         'gamma_wet': 0,
#         'phi': 0},
#     {
#         'name': 'Robertson zone 1',
#         'ui_name': 'Grond, fijn korrelig',
#         'color': '200, 25, 0',
#         'gamma_dry': 10,
#         'gamma_wet': 10,
#         'phi': 15},
#     {
#         'name': 'Robertson zone 2',
#         'ui_name': 'Veen, organisch materiaal',
#         'color': '188, 104, 67',
#         'gamma_dry': 12,
#         'gamma_wet': 12,
#         'phi': 15},
#     {
#         'name': 'Robertson zone 3',
#         'ui_name': 'Klei, zwak siltig tot siltig',
#         'color': '29, 118, 29',
#         'gamma_dry': 15.5,
#         'gamma_wet': 15.5,
#         'phi': 17.5},
#     {
#         'name': 'Robertson zone 4',
#         'ui_name': 'Klei, siltig / leem',
#         'color': '213, 252, 181',
#         'gamma_dry': 18,
#         'gamma_wet': 18,
#         'phi': 22.5},
#     {
#         'name': 'Robertson zone 5',
#         'ui_name': 'Zand, siltig tot leem',
#         'color': '213, 252, 155',
#         'gamma_dry': 18,
#         'gamma_wet': 20,
#         'phi': 25},
#     {
#         'name': 'Robertson zone 6',
#         'ui_name': 'Zand, zwak siltig tot siltig',
#         'color': '255, 225, 178',
#         'gamma_dry': 18,
#         'gamma_wet': 20,
#         'phi': 27},
#     {
#         'name': 'Robertson zone 7',
#         'ui_name': 'Zand tot zand, grindig',
#         'color': '255, 183, 42',
#         'gamma_dry': 17,
#         'gamma_wet': 19,
#         'phi': 32.5},
#     {
#         'name': 'Robertson zone 8',
#         'ui_name': 'Zand, vast - zand, kleiig',
#         'color': '200, 190, 200',
#         'gamma_dry': 18,
#         'gamma_wet': 20,
#         'phi': 32.5},
#     {
#         'name': 'Robertson zone 9',
#         'ui_name': 'Grond, zeer stijf, fijnkorrelig',
#         'color': '186, 205, 224',
#         'gamma_dry': 20,
#         'gamma_wet': 22,
#         'phi': 40}
# ]
#
# DEFAULT_CLASSIFICATION_TABLE = [
#     {
#         'phi': 30,
#         'name': 'Zand, schoon, los',
#         'color': '255,255,153',
#         'qc_max': None,
#         'qc_min': None,
#         'rf_max': 0.8,
#         'rf_min': None,
#         'gamma_dry': 17,
#         'gamma_wet': 19,
#         'qc_norm_max': 5,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 32.5,
#         'name': 'Zand, schoon, matig',
#         'color': '255,255,102',
#         'qc_max': None,
#         'qc_min': None,
#         'rf_max': 0.8,
#         'rf_min': None,
#         'gamma_dry': 18,
#         'gamma_wet': 20,
#         'qc_norm_max': 15,
#         'qc_norm_min': 5,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 35,
#         'name': 'Zand, schoon, vast',
#         'color': '255,255,0',
#         'qc_max': None,
#         'qc_min': None,
#         'rf_max': 0.8,
#         'rf_min': None,
#         'gamma_dry': 19,
#         'gamma_wet': 21,
#         'qc_norm_max': None,
#         'qc_norm_min': 15,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 27,
#         'name': 'Zand, zwak siltig',
#         'color': '255,204,102',
#         'qc_max': None,
#         'qc_min': None,
#         'rf_max': 1.5,
#         'rf_min': 0.8,
#         'gamma_dry': 18,
#         'gamma_wet': 20,
#         'qc_norm_max': None,
#         'qc_norm_min': 0,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 25,
#         'name': 'Zand, sterk siltig',
#         'color': '255,204,0',
#         'qc_max': None,
#         'qc_min': None,
#         'rf_max': 1.8,
#         'rf_min': 1.5,
#         'gamma_dry': 18,
#         'gamma_wet': 20,
#         'qc_norm_max': None,
#         'qc_norm_min': 0,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 17.5,
#         'name': 'Klei, schoon, slap',
#         'color': '0,255,0',
#         'qc_max': 0.75,
#         'qc_min': None,
#         'rf_max': 5,
#         'rf_min': 3,
#         'gamma_dry': 14,
#         'gamma_wet': 14,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 17.5,
#         'name': 'Klei, schoon, matig',
#         'color': '0,204,0',
#         'qc_max': 1.5,
#         'qc_min': 0.75,
#         'rf_max': 5,
#         'rf_min': 3,
#         'gamma_dry': 17,
#         'gamma_wet': 17,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 17.5,
#         'name': 'Klei, schoon, vast',
#         'color': '0,204,102',
#         'qc_max': None,
#         'qc_min': 1.5,
#         'rf_max': 5,
#         'rf_min': 3,
#         'gamma_dry': 19,
#         'gamma_wet': 19,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 22.5,
#         'name': 'Klei, zwak zandig',
#         'color': '102,255,102',
#         'qc_max': None,
#         'qc_min': 0,
#         'rf_max': 3,
#         'rf_min': 1.8,
#         'gamma_dry': 18,
#         'gamma_wet': 18,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 27.5,
#         'name': 'Klei, sterk zandig',
#         'color': '102,255,51',
#         'qc_max': None,
#         'qc_min': 0,
#         'rf_max': 3,
#         'rf_min': 1.8,
#         'gamma_dry': 18,
#         'gamma_wet': 18,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 15,
#         'name': 'Klei, organisch, slap',
#         'color': '102,153,0',
#         'qc_max': 0.2,
#         'qc_min': None,
#         'rf_max': 7,
#         'rf_min': 5,
#         'gamma_dry': 13,
#         'gamma_wet': 13,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 15,
#         'name': 'Klei, organisch, matig',
#         'color': '0,153,0',
#         'qc_max': None,
#         'qc_min': 0.2,
#         'rf_max': 7,
#         'rf_min': 5,
#         'gamma_dry': 15,
#         'gamma_wet': 15,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 15,
#         'name': 'Veen niet voorbelast slap',
#         'color': '204,153,0',
#         'qc_max': 0.1,
#         'qc_min': None,
#         'rf_max': None,
#         'rf_min': 7,
#         'gamma_dry': 10,
#         'gamma_wet': 10,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'},
#     {
#         'phi': 15,
#         'name': 'Veen matig voorbelast matig',
#         'color': '153,102,51',
#         'qc_max': None,
#         'qc_min': 0.1,
#         'rf_max': None,
#         'rf_min': 7,
#         'gamma_dry': 12,
#         'gamma_wet': 12,
#         'qc_norm_max': None,
#         'qc_norm_min': None,
#         'max_cone_res_mpa': 0,
#         'max_cone_res_type': 'Standard'}
# ]
#
# CLASSIFICATION_METHODS = [
#     OptionListElement(label='Robertson Method (Fugro)', value='robertson'),
# ]
#
# MAX_CONE_RESISTANCE_TYPE = [
#     OptionListElement('Standard'),
#     OptionListElement('Manual')
# ]
#
# VALIDITY_RANGES = [
#     OptionListElement(label='25', value=25),
#     OptionListElement(label='50', value=50),
#     OptionListElement(label='100', value=100),
# ]
#
# vis_robertson = IsEqual(Lookup('soil_interpretation.classification.method'), 'robertson')
# vis_t_m = IsEqual(Lookup('soil_interpretation.classification.method'), 'table')
# vis_crux = IsEqual(Lookup('soil_interpretation.classification.method'), 'crux')
# vis_crux_table = And(vis_crux, IsTrue(Lookup('soil_interpretation.classification.crux_overrule')))
# vis_single_section = IsFalse(Lookup("sections.visualization.connect_sections"))
#
#
# def _get_cpt_entities(entity_id: int) -> EntityList:
#     """Obtains the CPT entities"""
#     return API().get_entity(entity_id).children(entity_type_names=['CPTFile'], include_params=False)
#
#
# def _get_cpt_options(entity_id: int, **kwargs) -> List[OptionListElement]:
#     """Retrieves all CPT files options under the project entity"""
#     return [OptionListElement(entity.id, entity.name) for entity in _get_cpt_entities(entity_id)]


class SampleParametrization(Parametrization):
    """Defines the input fields in left-side of the web UI in the Sample entity (Editor)."""
    # soil_interpretation = Tab('Soil Interpretation')
    # soil_interpretation.classification = Section('Classification')
    # soil_interpretation.classification.method = OptionField('Classification method', options=CLASSIFICATION_METHODS,
    #                                                         default='robertson')
    # soil_interpretation.classification.robertson = TableInput('Robertson table', default=DEFAULT_ROBERTSON_TABLE,
    #                                                           visible=vis_robertson)
    # soil_interpretation.classification.robertson.name = TextField('Robertson Zone')
    # soil_interpretation.classification.robertson.ui_name = OptionField('Soil', options=DEFAULT_SOIL_NAMES)
    # soil_interpretation.classification.robertson.color = TextField('Color (R, G, B)')
    # soil_interpretation.classification.robertson.gamma_dry = NumberField('γ dry [kN/m³]',
    #                                                                      num_decimals=1)
    # soil_interpretation.classification.robertson.gamma_wet = NumberField('γ wet [kN/m³]', num_decimals=1)
    # soil_interpretation.classification.robertson.phi = NumberField('Friction angle Phi [°]', num_decimals=1)
    #
    # soil_interpretation.classification.table = TableInput('Classification table', default=DEFAULT_CLASSIFICATION_TABLE,
    #                                                       visible=vis_t_m)
    # soil_interpretation.classification.table.name = OptionField('Naam', options=DEFAULT_SOIL_NAMES)
    # soil_interpretation.classification.table.color = TextField('Kleur (R, G, B)')
    # soil_interpretation.classification.table.qc_min = NumberField('qc min [MPa]', num_decimals=2)
    # soil_interpretation.classification.table.qc_max = NumberField('qc max [MPa]', num_decimals=2)
    # soil_interpretation.classification.table.qc_norm_min = NumberField('qc norm; min [MPa]', num_decimals=1)
    # soil_interpretation.classification.table.qc_norm_max = NumberField('qc norm; max [MPa]', num_decimals=1)
    # soil_interpretation.classification.table.rf_min = NumberField('Rf min [%]', num_decimals=1)
    # soil_interpretation.classification.table.rf_max = NumberField('Rf max [%]', num_decimals=1)
    # soil_interpretation.classification.table.gamma_dry = NumberField('γ dry [kN/m³]', num_decimals=1)
    # soil_interpretation.classification.table.gamma_wet = NumberField('γ wet [kN/m³]', num_decimals=1)
    # soil_interpretation.classification.table.phi = NumberField('Friction angle Phi [°]', num_decimals=1)
    # soil_interpretation.classification.table.max_cone_res_type = OptionField('Maximum cone resistance type',
    #                                                                          options=MAX_CONE_RESISTANCE_TYPE)
    # soil_interpretation.classification.table.max_cone_res_mpa = NumberField('Maximum cone resistance [MPa]',
    #                                                                         num_decimals=1)
    #
    # soil_interpretation.classification.crux_overrule = ToggleButton('Overrule NEN table', default=False,
    #                                                                 visible=vis_crux)
    # soil_interpretation.classification.crux = TableInput('CRUX Overrule Classification table', visible=vis_crux_table,
    #                                                      default=DEFAULT_CLASSIFICATION_TABLE)
    # soil_interpretation.classification.crux.name = OptionField('Naam', options=DEFAULT_SOIL_NAMES)
    # soil_interpretation.classification.crux.color = TextField('Kleur (R, G, B)')
    # soil_interpretation.classification.crux.qc_min = NumberField('qc<sub>min</sub> [MPa]', num_decimals=2)
    # soil_interpretation.classification.crux.qc_max = NumberField('qc<sub>max</sub> [MPa]', num_decimals=2)
    # soil_interpretation.classification.crux.qc_norm_min = NumberField('qc<sub>norm; min</sub> [MPa]', num_decimals=1)
    # soil_interpretation.classification.crux.qc_norm_max = NumberField('qc<sub>norm; max</sub> [MPa]', num_decimals=1)
    # soil_interpretation.classification.crux.rf_min = NumberField('Rf<sub>min</sub> [%]', num_decimals=1)
    # soil_interpretation.classification.crux.rf_max = NumberField('Rf<sub>max</sub> [%]', num_decimals=1)
    # soil_interpretation.classification.crux.gamma_dry = NumberField('γ<sub>dry</sub> [kN/m\u00B3]', num_decimals=1)
    # soil_interpretation.classification.crux.gamma_wet = NumberField('γ<sub>wet</sub> [kN/m\u00B3]', num_decimals=1)
    # soil_interpretation.classification.crux.phi = NumberField('Friction angle Phi [\u00B0]', num_decimals=1)
    # soil_interpretation.classification.crux.max_cone_res_type = OptionField('Maximum cone resistance type',
    #                                                                         options=MAX_CONE_RESISTANCE_TYPE)
    # soil_interpretation.classification.crux.max_cone_res_mpa = NumberField('Maximum cone resistance [MPa]',
    #                                                                        num_decimals=1)
    # soil_interpretation.classification.reclassify_all_cpt_files = SetParamsButton('Reclassify soil layouts',
    #                                                                               method='reclassify_all_cpts',
    #                                                                               longpoll=True)
    # soil_interpretation.filtering = Section('Filtering')
    # soil_interpretation.filtering.filter_all_cpt_files = SetParamsButton('Filter soil layouts', 'filter_all_cpts',
    #                                                                      longpoll=True)
    # soil_interpretation.filtering.min_layer_thickness = NumberField('Minimum Layer Thickness', suffix='mm', min=0,
    #                                                                 step=50, default=DEFAULT_MIN_LAYER_THICKNESS)
    # soil_interpretation.downloads = Section('Downloads')
    # soil_interpretation.downloads.classification_plot = DownloadButton('Download Classification plot',
    #                                                                    'download_classification_plot')
    # soil_interpretation.downloads.csv_download = DownloadButton('Download CPT data CSV', 'download_csv')
