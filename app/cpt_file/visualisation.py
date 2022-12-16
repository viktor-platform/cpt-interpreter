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
from math import floor

from munch import Munch, unmunchify
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from viktor.geo import GEFData, SoilLayout

from .soil_layout_conversion_functions import (
    Classification,
    convert_input_table_field_to_soil_layout,
    filter_nones_from_params_dict,
)


def visualise_cpt(cpt_params: Munch):

    # parse input file and user input
    classification = Classification(cpt_params.classification)
    cpt_params = unmunchify(cpt_params)
    parsed_cpt = GEFData(filter_nones_from_params_dict(cpt_params))
    soil_layout_original = SoilLayout.from_dict(cpt_params["soil_layout_original"])
    soil_layout_user = convert_input_table_field_to_soil_layout(
        bottom_of_soil_layout_user=cpt_params["bottom_of_soil_layout_user"],
        soil_layers_from_table_input=cpt_params["soil_layout"],
        soils=classification.soil_mapping,
    )

    # Create plotly figure
    fig = make_subplots(
        rows=1,
        cols=3,
        shared_yaxes=True,
        horizontal_spacing=0.00,
        column_widths=[3.5, 1.5, 2],
        subplot_titles=("Cone Resistance", "Friction ratio", "Soil Layout"),
    )

    # add left side of the figure: Qc and Rf plot
    fig.add_trace(  # Add the qc curve
        go.Scatter(
            name="Cone Resistance",
            x=parsed_cpt.qc,
            y=[el * 1e-3 for el in parsed_cpt.elevation],
            mode="lines",
            line=dict(color="mediumblue", width=1),
            legendgroup="Cone Resistance",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(  # Add the Rf curve
        go.Scatter(
            name="Friction ratio",
            x=[rfval * 100 if rfval else rfval for rfval in parsed_cpt.Rf],
            y=[el * 1e-3 if el else el for el in parsed_cpt.elevation],
            mode="lines",
            line=dict(color="red", width=1),
            legendgroup="Friction ratio",
        ),
        row=1,
        col=2,
    )

    # add the bars on the right side of the plot
    add_soil_layout_to_fig(fig, soil_layout_original, soil_layout_user)

    # plot phreatic level
    fig.add_hline(
        y=cpt_params["ground_water_level"],
        line=dict(color="Blue", dash="dash", width=1),
        row="all",
        col="all",
    )

    update_fig_layout(fig, parsed_cpt)
    return fig


def update_fig_layout(fig, parsed_cpt):
    """Updates layout of the figure and formats the grids"""
    fig.update_layout(barmode="stack", template="plotly_white", legend=dict(x=1.15, y=0.5))
    fig.update_annotations(font_size=12)
    # Format axes and grids per subplot
    standard_grid_options = dict(showgrid=True, gridwidth=1, gridcolor="LightGrey")
    standard_line_options = dict(showline=True, linewidth=2, linecolor="LightGrey")

    # update x-axis for Qc
    fig.update_xaxes(
        row=1,
        col=1,
        **standard_line_options,
        **standard_grid_options,
        range=[0, 30],
        tick0=0,
        dtick=5,
        title_text="qc [MPa]",
        title_font=dict(color="mediumblue"),
    )
    # update x-axis for Rf
    fig.update_xaxes(
        row=1,
        col=2,
        **standard_line_options,
        **standard_grid_options,
        range=[9.9, 0],
        tick0=0,
        dtick=5,
        title_text="Rf [%]",
        title_font=dict(color="red"),
    )

    # update all y axis to ensure they line up
    fig.update_yaxes(
        row=1,
        col=1,
        **standard_grid_options,
        title_text="Depth [m] w.r.t. NAP",
        tick0=floor(parsed_cpt.elevation[-1] / 1e3) - 5,
        dtick=1,
    )  # for Qc

    fig.update_yaxes(
        row=1,
        col=2,
        **standard_line_options,
        **standard_grid_options,  # for Rf
        tick0=floor(parsed_cpt.elevation[-1] / 1e3) - 5,
        dtick=1,
    )

    fig.update_yaxes(
        row=1,
        col=3,
        **standard_line_options,  # for soil layouts
        tick0=floor(parsed_cpt.elevation[-1] / 1e3) - 5,
        dtick=1,
        showticklabels=True,
        side="right",
    )


def add_soil_layout_to_fig(fig, soil_layout_original, soil_layout_user):
    """Add bars for each soil type separately in order to be able to set legend labels"""
    unique_soil_types = {
        layer.soil.properties.ui_name for layer in [*soil_layout_original.layers, *soil_layout_user.layers]
    }
    for ui_name in unique_soil_types:
        original_layers = [layer for layer in soil_layout_original.layers if layer.soil.properties.ui_name == ui_name]
        interpreted_layers = [layer for layer in soil_layout_user.layers if layer.soil.properties.ui_name == ui_name]
        soil_type_layers = [
            *original_layers,
            *interpreted_layers,
        ]  # have a list of all soils used in both figures

        # add the bar plots to the figures
        fig.add_trace(
            go.Bar(
                name=ui_name,
                x=["Original"] * len(original_layers) + ["Interpreted"] * len(interpreted_layers),
                y=[-layer.thickness * 1e-3 for layer in soil_type_layers],
                width=0.5,
                marker_color=[f"rgb{layer.soil.color.rgb}" for layer in soil_type_layers],
                hovertext=[
                    f"Soil Type: {layer.soil.properties.ui_name}<br>"
                    f"Top of layer: {layer.top_of_layer * 1e-3:.2f}<br>"
                    f"Bottom of layer: {layer.bottom_of_layer * 1e-3:.2f}"
                    for layer in soil_type_layers
                ],
                hoverinfo="text",
                base=[layer.top_of_layer * 1e-3 for layer in soil_type_layers],
            ),
            row=1,
            col=3,
        )
