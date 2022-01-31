from io import StringIO
from math import floor
from typing import List

from munch import Munch
from munch import munchify
from munch import unmunchify
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from viktor import UserException
from viktor.geo import GEFData
from viktor.geo import SoilLayout
from viktor.geometry import Point
from viktor.geometry import RDWGSConverter
from viktor.views import MapEntityLink
from viktor.views import MapPoint
from .soil_layout_conversion_functions import \
    convert_input_table_field_to_soil_layout


class CPT:
    def __init__(self, cpt_params, soils=None, entity_id=None, **kwargs):
        params = unmunchify(cpt_params)
        self.headers = munchify(params['headers'])
        self.params = params
        self.parsed_cpt = GEFData(self.filter_nones_from_params_dict(params))
        self.soil_layout_original = SoilLayout.from_dict(params['soil_layout_original'])
        self.bottom_of_soil_layout_user = self.soil_layout_original.bottom / 1e3
        self.ground_water_level = params['ground_water_level']
        self.name = params['name']
        self.id = entity_id

        self._soils = soils
        self._params_soil_layout = params['soil_layout']

    @property
    def soil_layout(self) -> SoilLayout:
        """Returns a soil layout based on the input table"""
        return convert_input_table_field_to_soil_layout(self.bottom_of_soil_layout_user,
                                                        self._params_soil_layout, self._soils)

    @property
    def entity_link(self) -> MapEntityLink:
        """Returns a MapEntity link to the GEF entity, which is used in the MapView of the Project entity"""
        return MapEntityLink(self.name, self.id)

    @staticmethod
    def filter_nones_from_params_dict(raw_dict) -> dict:
        """Removes all rows which contain one or more None-values"""
        rows_to_be_removed = []
        for row_index, items in enumerate(zip(*raw_dict['measurement_data'].values())):
            if None in items:
                rows_to_be_removed.append(row_index)
        for row in reversed(rows_to_be_removed):
            for signal in raw_dict['measurement_data'].keys():
                del raw_dict['measurement_data'][signal][row]
        return raw_dict

    @property
    def coordinates(self) -> Point:
        """Returns a Point object of the x-y coordinates to be used in geographic calculations"""
        if not hasattr(self.parsed_cpt, 'x_y_coordinates') or None in self.parsed_cpt.x_y_coordinates:
            raise UserException(f"CPT {self.name} has no coordinates: please check the CPT file")
        return Point(self.parsed_cpt.x_y_coordinates[0], self.parsed_cpt.x_y_coordinates[1])

    @property
    def wgs_coordinates(self) -> Munch:
        """Returns a dictionary of the lat lon coordinates to be used in geographic calculations"""
        if not hasattr(self.parsed_cpt, 'x_y_coordinates') or None in self.parsed_cpt.x_y_coordinates:
            raise UserException(f"CPT {self.name} has no coordinates: please check the GEF file")
        lat, lon = RDWGSConverter.from_rd_to_wgs(self.parsed_cpt.x_y_coordinates)
        return munchify({"lat": lat, "lon": lon})

    def get_map_point(self):
        """Returns a MapPoint object with a specific color"""
        return MapPoint(self.wgs_coordinates.lat, self.wgs_coordinates.lon, title=self.name,
                        description=f"RD coordinaten: {self.coordinates.x}, {self.coordinates.y}",
                        entity_links=[self.entity_link])

    def visualize(self) -> StringIO:
        """Creates an interactive plot using plotly, showing the same information as the static visualization"""
        fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.00, column_widths=[3.5, 1.5, 2],
                            subplot_titles=("Cone Resistance", "Friction ratio", "Soil Layout"))
        # Add Qc plot
        fig.add_trace(
            go.Scatter(name='Cone Resistance',
                       x=self.parsed_cpt.qc,
                       y=[el * 1e-3 for el in self.parsed_cpt.elevation],
                       mode='lines',
                       line=dict(color='mediumblue', width=1),
                       legendgroup="Cone Resistance"),
            row=1, col=1
        )

        # Add Rf plot
        fig.add_trace(
            go.Scatter(name='Friction ratio',
                       x=[rfval * 100 if rfval else rfval for rfval in self.parsed_cpt.Rf],
                       y=[el * 1e-3 if el else el for el in self.parsed_cpt.elevation],
                       mode='lines',
                       line=dict(color='red', width=1),
                       legendgroup="Friction ratio"),
            row=1, col=2
        )

        # Add fs plot
        fig.add_trace(
            go.Scatter(name='Sleeve friction',
                       x=self.parsed_cpt.fs if self.parsed_cpt.fs else
                       [qc / rfval for qc, rfval in zip(self.parsed_cpt.qc, self.parsed_cpt.rfval)],
                       y=[el * 1e-3 if el else el for el in self.parsed_cpt.elevation],
                       visible=False,
                       mode='lines',
                       line=dict(color='red', width=1),
                       legendgroup="Sleeve friction"),
            row=1, col=2
        )

        # Add bars for each soil type separately in order to be able to set legend labels
        unique_soil_types = {layer.soil.properties.ui_name for layer in [*self.soil_layout_original.layers,
                                                                         *self.soil_layout.layers]}

        for ui_name in unique_soil_types:
            original_layers = [layer for layer in self.soil_layout_original.layers
                               if layer.soil.properties.ui_name == ui_name]
            interpreted_layers = [layer for layer in self.soil_layout.layers
                                  if layer.soil.properties.ui_name == ui_name]

            soil_type_layers = [*original_layers, *interpreted_layers]
            fig.add_trace(go.Bar(name=ui_name,
                                 x=['Original'] * len(original_layers) + ['Interpreted'] * len(interpreted_layers),
                                 y=[-layer.thickness * 1e-3 for layer in soil_type_layers],
                                 width=0.5,
                                 marker_color=[f"rgb{layer.soil.color.rgb}" for layer in soil_type_layers],
                                 hovertext=[f"Soil Type: {layer.soil.properties.ui_name}<br>"
                                            f"Top of layer: {layer.top_of_layer * 1e-3:.2f}<br>"
                                            f"Bottom of layer: {layer.bottom_of_layer * 1e-3:.2f}"
                                            for layer in soil_type_layers],
                                 hoverinfo='text',
                                 base=[layer.top_of_layer * 1e-3 for layer in soil_type_layers]),
                          row=1, col=3)

        # Add dashed blue line representing phreatic level, and solid black line for ground level
        fig.add_hline(y=self.ground_water_level, line=dict(color='Blue', dash='dash', width=1),
                      row='all', col='all')

        # fig.add_hline(y=self.parsed_cpt.elevation[0] * 1e-3, line=dict(color='Black', width=1),
        #               row='all', col='all') #TODO Horizontal line for groundlevel: a bit ugly

        fig.update_layout(barmode='stack', template='plotly_white', legend=dict(x=1.05, y=0.5))

        # Format axes and grids per subplot
        standard_grid_options = dict(showgrid=True, gridwidth=1, gridcolor='LightGrey')
        standard_line_options = dict(showline=True, linewidth=2, linecolor='LightGrey')

        fig.update_xaxes(row=1, col=1, **standard_line_options, **standard_grid_options,
                         range=[0, 30], tick0=0, dtick=5, title_text="qc [MPa]", title_font=dict(color='mediumblue'))
        fig.update_xaxes(row=1, col=2, **standard_line_options, **standard_grid_options,
                         range=[9.9, 0], tick0=0, dtick=5, title_text="Rf [%]", title_font=dict(color='red'))

        fig.update_yaxes(row=1, col=1, **standard_grid_options, title_text="Depth [m] w.r.t. NAP",
                         tick0=floor(self.parsed_cpt.elevation[-1] / 1e3) - 5, dtick=1)
        fig.update_yaxes(row=1, col=2, **standard_line_options, **standard_grid_options,
                         tick0=floor(self.parsed_cpt.elevation[-1] / 1e3) - 5, dtick=1)
        fig.update_yaxes(row=1, col=3, **standard_line_options,
                         tick0=floor(self.parsed_cpt.elevation[-1] / 1e3) - 5, dtick=1,
                         showticklabels=True, side='right')

        # Button switch Rf/fs
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=list([
                        dict(
                            args=[{'visible': [True, True, False] + [True] * len(unique_soil_types)},
                                  {'xaxis2.title': 'Rf [%]', 'xaxis2.range': [9.9, 0], 'xaxis2.dtick': 5},

                                  ],
                            label="Rf",
                            method="update"
                        ),
                        dict(
                            args=[{'visible': [True, False, True] + [True] * len(unique_soil_types)},
                                  {'xaxis2.title': 'fs [MPa]', 'xaxis2.range': [0.499, 0], 'xaxis2.dtick': 0.1},
                                  ],
                            label="fs",
                            method="update"
                        )
                    ]),
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=1.11,
                    xanchor="left",
                    y=1.1,
                    yanchor="top"
                ),
            ]
        )
        return StringIO(fig.to_html())


def color_coded_cpt_map_points(cpt_models: List[CPT]) -> List[MapPoint]:
    """Function that assigns correct color to CPT based on location wrt. Polyline or exclusion"""
    map_features = []
    for cpt in cpt_models:
        map_features.append(cpt.get_map_point())
    return map_features

