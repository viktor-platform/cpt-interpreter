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

from viktor.errors import UserError
from viktor.parametrization import (
    And,
    BooleanField,
    DownloadButton,
    FileField,
    HiddenField,
    IsEqual,
    IsFalse,
    Lookup,
    NumberField,
    OptionField,
    OptionListElement,
    Parametrization,
    SetParamsButton,
    Step,
    TableInput,
    Text,
    TextField,
)

from .constants import (
    DEFAULT_CLASSIFICATION_TABLE,
    DEFAULT_MIN_LAYER_THICKNESS,
    DEFAULT_ROBERTSON_TABLE,
    DEFAULT_SOIL_NAMES,
    MAX_CONE_RESISTANCE_TYPE,
)

CLASSIFICATION_METHODS = [
    OptionListElement(label="Robertson Method (Fugro)", value="robertson"),
    OptionListElement(label="Table Method", value="table"),
]


def validate_step_1(params, **kwargs):
    """Validates step 1."""
    if not params.measurement_data:
        raise UserError("Classify soil layout before proceeding.")


class CPTFileParametrization(Parametrization):
    """Defines the input fields in left-side of the web UI in the CPT_file entity (Editor)."""

    classification = Step("Upload and classification", on_next=validate_step_1)
    classification.text_01 = Text(
        """# Welcome to the CPT interpretation app!

With this app you will be able to classify and interpret GEF-formatted CPT files by uploading and automatically 
classifying the soil profile based on the classification table.

## Step 1: Upload a GEF file

For the users who want to try out the app, but do not have a GEF file at hand, feel free to use the sample 
GEF file available.
    """
    )
    classification.gef_file = FileField(
        "Upload GEF file",
        file_types=[".gef"],
        visible=IsFalse(Lookup("classification.get_sample_gef_toggle")),
    )
    classification.get_sample_gef_toggle = BooleanField("Get sample GEF file", default=False, flex=15)
    classification.download_sample_gef = DownloadButton(
        "Download sample GEF file",
        "download_sample_gef_file",
        visible=Lookup("classification.get_sample_gef_toggle"),
        flex=15,
    )
    classification.text_02 = Text(
        """## Step 2: Select your classification method
        
Select your preferred classification method.
        """
    )
    classification.method = OptionField(
        "Classification method",
        options=CLASSIFICATION_METHODS,
        default="robertson",
        autoselect_single_option=True,
        variant="radio-inline",
        description="Robertson method: Robertson method, optimized for the dutch soil by Fugro. \n"
        "\n Table method: Custom classification.",
    )
    classification.change_table = BooleanField("Change classification table")
    classification.robertson = TableInput(
        "Robertson table",
        default=DEFAULT_ROBERTSON_TABLE,
        visible=And(
            Lookup("classification.change_table"),
            IsEqual(Lookup("classification.method"), "robertson"),
        ),
    )
    classification.robertson.name = TextField("Robertson Zone")
    classification.robertson.ui_name = OptionField("Soil", options=DEFAULT_SOIL_NAMES)
    classification.robertson.color = TextField("Color (R, G, B)")
    classification.robertson.gamma_dry = NumberField("γ dry [kN/m³]", num_decimals=1)
    classification.robertson.gamma_wet = NumberField("γ wet [kN/m³]", num_decimals=1)
    classification.robertson.phi = NumberField("Friction angle Phi [°]", num_decimals=1)

    classification.table = TableInput(
        "Classification table",
        default=DEFAULT_CLASSIFICATION_TABLE,
        visible=And(
            Lookup("classification.change_table"),
            IsEqual(Lookup("classification.method"), "table"),
        ),
    )
    classification.table.name = OptionField("Naam", options=DEFAULT_SOIL_NAMES)
    classification.table.color = TextField("Kleur (R, G, B)")
    classification.table.qc_min = NumberField("qc min [MPa]", num_decimals=2)
    classification.table.qc_max = NumberField("qc max [MPa]", num_decimals=2)
    classification.table.qc_norm_min = NumberField("qc norm; min [MPa]", num_decimals=1)
    classification.table.qc_norm_max = NumberField("qc norm; max [MPa]", num_decimals=1)
    classification.table.rf_min = NumberField("Rf min [%]", num_decimals=1)
    classification.table.rf_max = NumberField("Rf max [%]", num_decimals=1)
    classification.table.gamma_dry = NumberField("γ dry [kN/m³]", num_decimals=1)
    classification.table.gamma_wet = NumberField("γ wet [kN/m³]", num_decimals=1)
    classification.table.phi = NumberField("Friction angle Phi [°]", num_decimals=1)
    classification.table.max_cone_res_type = OptionField(
        "Maximum cone resistance type", options=MAX_CONE_RESISTANCE_TYPE
    )
    classification.table.max_cone_res_mpa = NumberField("Maximum cone resistance [MPa]", num_decimals=1)
    classification.text_03 = Text(
        """## Step 3: Classify the soil layout
        
Classify the uploaded GEF file by clicking the "Classify soil layout" button. Proceed then to the next step.
        """
    )
    classification.classify_soil_layout_button = SetParamsButton("Classify soil layout", "classify_soil_layout")

    cpt = Step("CPT interpretation", views=["visualize_cpt", "visualize_map"])
    cpt.text = Text(
        "Use the table below to change the interpreted soil layout by changing the positions of the layers, "
        "adding rows or changing the material type."
    )

    cpt.filter_thin_layers = SetParamsButton(
        "Filter Layer Thickness",
        method="filter_soil_layout_on_min_layer_thickness",
        flex=60,
        description="Filter the soil layout to remove layers that are " "thinner than the minimum layer thickness",
    )
    cpt.min_layer_thickness = NumberField(
        "Minimum Layer Thickness",
        suffix="mm",
        min=0,
        step=50,
        default=DEFAULT_MIN_LAYER_THICKNESS,
        flex=40,
    )

    cpt.reset_original_layers = SetParamsButton(
        "Reset to original Soil Layout",
        method="reset_soil_layout_user",
        flex=100,
        description="Reset the table to the original soil layout",
    )

    cpt.ground_water_level = NumberField("Phreatic level", name="ground_water_level", suffix="m NAP", flex=50)
    cpt.ground_level = NumberField("Ground level", name="ground_level", suffix="m NAP", flex=50)
    cpt.soil_layout = TableInput("Soil layout", name="soil_layout")
    cpt.soil_layout.name = OptionField("Material", options=DEFAULT_SOIL_NAMES)
    cpt.soil_layout.top_of_layer = NumberField("Top (m NAP)", num_decimals=1)

    # hidden fields
    cpt.gef_headers = HiddenField("GEF Headers", name="headers")
    cpt.bottom_of_soil_layout_user = HiddenField("GEF Soil bottom", name="bottom_of_soil_layout_user")
    cpt.measurement_data = HiddenField("GEF Measurement data", name="measurement_data")
    cpt.soil_layout_original = HiddenField("Soil layout original", name="soil_layout_original")

    final_step = Step("What's next?", views="final_step")
