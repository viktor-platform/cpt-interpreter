from viktor import Color
from viktor.parametrization import OptionListElement
from viktor.views import MapLegend

CPT_COLOR = Color.from_hex('#a86832')

CM2INCH = 1 / 2.54

DEFAULT_MIN_LAYER_THICKNESS = 200

ADDITIONAL_COLUMNS = ['corrected_depth', 'fs', 'u2', 'inclination', 'inclination_n_s', 'inclination_e_w']

DEFAULT_SOIL_NAMES = [
    OptionListElement('Grind, zwak siltig, los'),
    OptionListElement('Grind, zwak siltig, matig'),
    OptionListElement('Grind, zwak siltig, vast'),
    OptionListElement('Grind, sterk siltig, los'),
    OptionListElement('Grind, sterk siltig, matig'),
    OptionListElement('Grind, sterk siltig, vast'),
    OptionListElement('Zand, schoon, los'),
    OptionListElement('Zand, schoon, matig'),
    OptionListElement('Zand, schoon, vast'),
    OptionListElement('Zand, zwak siltig, kleiïg'),
    OptionListElement('Zand, sterk siltig, kleiïg'),
    OptionListElement('Leem, zwak zandig, slap'),
    OptionListElement('Leem, zwak zandig, matig'),
    OptionListElement('Leem, zwak zandig, vast'),
    OptionListElement('Leem, sterk zandig'),
    OptionListElement('Klei, schoon, slap'),
    OptionListElement('Klei, schoon, matig'),
    OptionListElement('Klei, schoon, vast'),
    OptionListElement('Klei, zwak zandig, slap'),
    OptionListElement('Klei, zwak zandig, matig'),
    OptionListElement('Klei, zwak zandig, vast'),
    OptionListElement('Klei, sterk zandig'),
    OptionListElement('Klei, organisch, slap'),
    OptionListElement('Klei, organisch, matig'),
    OptionListElement('Veen, niet voorbelast, slap'),
    OptionListElement('Veen, matig voorbelast, matig'),
]

CPT_LEGEND = MapLegend([
    (Color.viktor_yellow(), "CPT"),
])
