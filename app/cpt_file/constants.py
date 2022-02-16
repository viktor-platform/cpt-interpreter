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

DEFAULT_MIN_LAYER_THICKNESS = 200

ADDITIONAL_COLUMNS = ['corrected_depth', 'fs', 'u2', 'inclination', 'inclination_n_s', 'inclination_e_w']

DEFAULT_ROBERTSON_TABLE = [
    {
        'name': 'Robertson zone unknown',
        'ui_name': 'Onbekend materiaal',
        'color': (255, 0, 0),
        'gamma_dry': 0,
        'gamma_wet': 0,
        'phi': 0},
    {
        'name': 'Robertson zone 1',
        'ui_name': 'Grond, fijn korrelig',
        'color': (200, 25, 0),
        'gamma_dry': 10,
        'gamma_wet': 10,
        'phi': 15},
    {
        'name': 'Robertson zone 2',
        'ui_name': 'Veen, organisch materiaal',
        'color': (188, 104, 67),
        'gamma_dry': 12,
        'gamma_wet': 12,
        'phi': 15},
    {
        'name': 'Robertson zone 3',
        'ui_name': 'Klei, zwak siltig tot siltig',
        'color': (29, 118, 29),
        'gamma_dry': 15.5,
        'gamma_wet': 15.5,
        'phi': 17.5},
    {
        'name': 'Robertson zone 4',
        'ui_name': 'Klei, siltig / leem',
        'color': (213, 252, 181),
        'gamma_dry': 18,
        'gamma_wet': 18,
        'phi': 22.5},
    {
        'name': 'Robertson zone 5',
        'ui_name': 'Zand, siltig tot leem',
        'color': (213, 252, 155),
        'gamma_dry': 18,
        'gamma_wet': 20,
        'phi': 25},
    {
        'name': 'Robertson zone 6',
        'ui_name': 'Zand, zwak siltig tot siltig',
        'color': (255, 225, 178),
        'gamma_dry': 18,
        'gamma_wet': 20,
        'phi': 27},
    {
        'name': 'Robertson zone 7',
        'ui_name': 'Zand tot zand, grindig',
        'color': (255, 183, 42),
        'gamma_dry': 17,
        'gamma_wet': 19,
        'phi': 32.5},
    {
        'name': 'Robertson zone 8',
        'ui_name': 'Zand, vast - zand, kleiig',
        'color': (200, 190, 200),
        'gamma_dry': 18,
        'gamma_wet': 20,
        'phi': 32.5},
    {
        'name': 'Robertson zone 9',
        'ui_name': 'Grond, zeer stijf, fijnkorrelig',
        'color': (186, 205, 224),
        'gamma_dry': 20,
        'gamma_wet': 22,
        'phi': 40}
]
