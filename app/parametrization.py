"""Copyright (c) 2024 VIKTOR B.V.

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

import viktor as vkt

from .constants import (
    DEFAULT_CLASSIFICATION_TABLE,
    DEFAULT_MIN_LAYER_THICKNESS,
    DEFAULT_ROBERTSON_TABLE,
    DEFAULT_SOIL_NAMES,
    MAX_CONE_RESISTANCE_TYPE,
)

CLASSIFICATION_METHODS = [
    vkt.OptionListElement(label="Robertson Method (Fugro)", value="robertson"),
    vkt.OptionListElement(label="Table Method", value="table"),
]


def validate_step_1(params, **kwargs):
    """Validates step 1."""
    if not params.measurement_data:
        raise vkt.UserError("Classify soil layout before proceeding.")


class Parametrization(vkt.ViktorParametrization):
    classification = vkt.Step("CPT classification", on_next=validate_step_1)
    classification.text_01 = vkt.Text(
        """# Welcome to the CPT interpretation app!

With this app you will be able to classify and interpret GEF-formatted CPT files by uploading and automatically 
classifying the soil profile based on the classification table.

## Step 1: Upload a GEF file

For the users who want to try out the app, but do not have a GEF file at hand, feel free to use the sample 
GEF file available.
    """
    )
    classification.gef_file = vkt.FileField(
        "Upload GEF file",
        file_types=[".gef"],
        visible=vkt.IsFalse(vkt.Lookup("classification.get_sample_gef_toggle")),
    )
    classification.get_sample_gef_toggle = vkt.BooleanField("Use sample GEF file", default=False, flex=15)
    classification.download_sample_gef = vkt.DownloadButton(
        "Download sample GEF file",
        method="download_sample_gef_file",
        visible=vkt.Lookup("classification.get_sample_gef_toggle"),
        flex=15,
    )
    classification.text_02 = vkt.Text(
        """## Step 2: Select your classification method
        
Select your preferred classification method.
        """
    )
    classification.method = vkt.OptionField(
        "Classification method",
        options=CLASSIFICATION_METHODS,
        default="robertson",
        variant="radio-inline",
        description="Robertson method: Robertson method, optimized for the dutch soil by Fugro. \n"
        "\n Table method: Custom classification.",
    )
    classification.change_table = vkt.BooleanField("Change classification table")
    classification.robertson = vkt.Table(
        "Robertson table",
        default=DEFAULT_ROBERTSON_TABLE,
        visible=vkt.And(
            vkt.Lookup("classification.change_table"),
            vkt.IsEqual(vkt.Lookup("classification.method"), "robertson"),
        ),
    )
    classification.robertson.name = vkt.TextField("Robertson Zone")
    classification.robertson.ui_name = vkt.OptionField("Soil", options=DEFAULT_SOIL_NAMES)
    classification.robertson.color = vkt.TextField("Color (R, G, B)")
    classification.robertson.gamma_dry = vkt.NumberField("γ dry [kN/m³]", num_decimals=1)
    classification.robertson.gamma_wet = vkt.NumberField("γ wet [kN/m³]", num_decimals=1)
    classification.robertson.phi = vkt.NumberField("Friction angle Phi [°]", num_decimals=1)

    classification.table = vkt.Table(
        "Classification table",
        default=DEFAULT_CLASSIFICATION_TABLE,
        visible=vkt.And(
            vkt.Lookup("classification.change_table"),
            vkt.IsEqual(vkt.Lookup("classification.method"), "table"),
        ),
    )
    classification.table.name = vkt.OptionField("Name", options=DEFAULT_SOIL_NAMES)
    classification.table.color = vkt.TextField("Color (R, G, B)")
    classification.table.qc_min = vkt.NumberField("qc min [MPa]", num_decimals=2)
    classification.table.qc_max = vkt.NumberField("qc max [MPa]", num_decimals=2)
    classification.table.qc_norm_min = vkt.NumberField("qc norm; min [MPa]", num_decimals=1)
    classification.table.qc_norm_max = vkt.NumberField("qc norm; max [MPa]", num_decimals=1)
    classification.table.rf_min = vkt.NumberField("Rf min [%]", num_decimals=1)
    classification.table.rf_max = vkt.NumberField("Rf max [%]", num_decimals=1)
    classification.table.gamma_dry = vkt.NumberField("γ dry [kN/m³]", num_decimals=1)
    classification.table.gamma_wet = vkt.NumberField("γ wet [kN/m³]", num_decimals=1)
    classification.table.phi = vkt.NumberField("Friction angle Phi [°]", num_decimals=1)
    classification.table.max_cone_res_type = vkt.OptionField(
        "Maximum cone resistance type", options=MAX_CONE_RESISTANCE_TYPE
    )
    classification.table.max_cone_res_mpa = vkt.NumberField("Maximum cone resistance [MPa]", num_decimals=1)
    classification.text_03 = vkt.Text(
        """## Step 3: Classify the soil layout
        
Classify the uploaded GEF file by clicking the button below. After classification you can proceed to the next step.
        """
    )
    classification.classify_soil_layout_button = vkt.SetParamsButton("Classify soil layout", method="classify_soil_layout")

    cpt = vkt.Step("CPT interpretation", views=["visualize_cpt", "visualize_map"])
    cpt.text = vkt.Text(
        "Use the table below to change the interpreted soil layout by changing the positions of the layers, "
        "adding rows or changing the material type."
    )

    cpt.min_layer_thickness = vkt.NumberField(
        "Minimum Layer Thickness",
        suffix="mm",
        min=0,
        step=50,
        default=DEFAULT_MIN_LAYER_THICKNESS,
        flex=50,
    )
    cpt.l1 = vkt.LineBreak()
    cpt.filter_thin_layers = vkt.SetParamsButton(
        "Filter Layer Thickness",
        method="filter_soil_layout_on_min_layer_thickness",
        flex=50,
        description="Filter the soil layout to remove layers that are " "thinner than the minimum layer thickness",
    )
    cpt.reset_original_layers = vkt.SetParamsButton(
        "Reset to original Soil Layout",
        method="reset_soil_layout_user",
        flex=50,
        description="Reset the table to the original soil layout",
    )

    cpt.ground_water_level = vkt.NumberField("Phreatic level", name="ground_water_level", suffix="m NAP", flex=50)
    cpt.soil_layout = vkt.Table("Soil layout", name="soil_layout")
    cpt.soil_layout.name = vkt.OptionField("Material", options=DEFAULT_SOIL_NAMES)
    cpt.soil_layout.top_of_layer = vkt.NumberField("Top (m NAP)", num_decimals=1)

    # hidden fields
    cpt.gef_headers = vkt.HiddenField("GEF Headers", name="headers")
    cpt.bottom_of_soil_layout_user = vkt.HiddenField("GEF Soil bottom", name="bottom_of_soil_layout_user")
    cpt.measurement_data = vkt.HiddenField("GEF Measurement data", name="measurement_data")
    cpt.soil_layout_original = vkt.HiddenField("Soil layout original", name="soil_layout_original")
