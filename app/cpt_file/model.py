from io import StringIO
from math import floor
from math import pi
from typing import Dict
from typing import List
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
from munch import Munch
from munch import munchify
from munch import unmunchify
from numpy import cos
from numpy import radians
from numpy import sin
from numpy.core import linspace
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from viktor import Color
from viktor import UserException
from viktor.geo import GEFData
from viktor.geo import SoilLayout
from viktor.geometry import Point
from viktor.geometry import RDWGSConverter
from viktor.views import MapEntityLink
from viktor.views import MapLabel
from viktor.views import MapPoint
from viktor.views import MapPoint
from viktor.views import MapPolygon

from .constants import CM2INCH
from .soil_layout_conversion_functions import \
    convert_input_table_field_to_soil_layout


class CPT():
    def __init__(self, cpt_params, soils=None, entity_id=None, **kwargs):
        params = unmunchify(cpt_params)
        self.headers = munchify(params['headers'])
        self.params = params
        self.parsed_cpt = GEFData(self.filter_nones_from_params_dict(params))
        self.soil_layout_original = SoilLayout.from_dict(params['soil_layout_original'])
        self.bottom_of_soil_layout_user = self.soil_layout_original.bottom / 1e3
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


def get_pdf_image_cpt_visualisation_scaled(plot_params: Munch, multi_gef_data: List[GEFData],
                                           soil_layout: Optional[SoilLayout] = None) -> List[Figure]:
    """Generate a list of plt figures to be displayed in a PDFView. Each element of the list is a different page of
    the PDF"""
    scaling_depth_factor = plot_params.format.scaling_factor  # scaling factor = cm per 1 meter depth

    if plot_params.format.paper_format == 'A3':
        figure_width, figure_height = 29.7, 42  # cm
        left = 0.10  # could be adjusted to the paper format
        bottom = 0.10
        axes_height_ratio = 0.78
    elif plot_params.format.paper_format == 'A2':
        figure_width, figure_height = 42, 59.3  # cm
        left = 0.10
        bottom = 0.10
        axes_height_ratio = 0.78
    elif plot_params.format.paper_format == 'A1':
        figure_width, figure_height = 59.3, 84.1  # cm
        left = 0.10
        bottom = 0.10
        axes_height_ratio = 0.78
    else:  # Else, assign A4 format
        figure_width, figure_height = 21, 29.7  # cm
        left = 0.10
        bottom = 0.10
        axes_height_ratio = 0.78

    axes_height_max = figure_height * axes_height_ratio
    axes_height_actual = np.floor(axes_height_max / scaling_depth_factor) * scaling_depth_factor
    qc_fs_axes_width = 15 * scaling_depth_factor  # 15 x-ticks for qc
    verticality_axes_width = 3 * scaling_depth_factor  # 3 x-ticks
    rf_axes_width = 5 * scaling_depth_factor  # 5 x-ticks for Rf
    nb_y_ticks_figure = np.floor(axes_height_max / scaling_depth_factor)  # Number of y-ticks per figure
    figsize = (figure_width * CM2INCH, figure_height * CM2INCH)

    rectangle_dict = {}
    rectangle_dict['info'] = [left, bottom + axes_height_actual / figure_height, 0.7,
                              1 - bottom - axes_height_actual / figure_height]
    rectangle_dict['conus'] = [left, bottom, qc_fs_axes_width / figure_width, axes_height_actual / figure_height]
    rectangle_dict['verticality'] = [left + rectangle_dict['conus'][2], bottom,
                                     verticality_axes_width / figure_width, axes_height_actual / figure_height]
    rectangle_dict['rf'] = [left + rectangle_dict['conus'][2] + rectangle_dict['verticality'][2], bottom,
                            rf_axes_width / figure_width, axes_height_actual / figure_height]

    figures = []
    y_start = plot_params.format.top_plot or np.ceil(plot_params.max_ground_level / 1e3) + 1
    y_end = min([gef_data.elevation[-1] / 1e3 for gef_data in multi_gef_data])
    ymax, page = y_start, 1
    nb_pages = int(np.ceil((y_start - y_end) / nb_y_ticks_figure))
    while ymax > y_end:  # A new page of the PDF is generated until the final depth y_end has been reached
        fig = make_figure(plot_params=plot_params, figsize=figsize, ymax=ymax, nb_y_ticks=nb_y_ticks_figure,
                          rectangle_dict=rectangle_dict, multi_gef_data=multi_gef_data, page=(page, nb_pages))
        figures.append(fig)
        plt.close(fig)  # Explicitly close figure to prevent possible memory issues
        ymax -= nb_y_ticks_figure
        page += 1

    return figures


def make_figure(plot_params: Munch, figsize: Tuple, ymax: int, nb_y_ticks: int, rectangle_dict: Dict[str, List],
                multi_gef_data: List[GEFData], page: Tuple[int, int]) -> Figure:
    """Make a plt figure, two cases are distinguished whether different CPTs are plotted on the same page or not"""
    figure = plt.figure(figsize=figsize)
    ymin = ymax - nb_y_ticks

    if not plot_params.selection.share_figure:
        gef_data = multi_gef_data[0]
        create_info_box(page, gef_data)
        create_conus_box_single(rect=rectangle_dict['conus'], ymin_ymax=[ymin, ymax], gef_data=gef_data)
        create_friction_ratio_box(rect=rectangle_dict['rf'], ymin_ymax=[ymin, ymax], gef_data=gef_data)
        if hasattr(gef_data, 'inclination'):
            create_verticality_box(rect=rectangle_dict['verticality'], ymin_ymax=[ymin, ymax], gef_data=gef_data)
        return figure

    # Else Plot CPTs on same page
    create_conus_box_multi(rect=rectangle_dict['conus'], ymin_ymax=[ymin, ymax], multi_gef_data=multi_gef_data)
    create_friction_ratio_box_multi(rect=rectangle_dict['rf'], ymin_ymax=[ymin, ymax],
                                    multi_gef_data=multi_gef_data)
    figure.legend(bbox_to_anchor=(0.1, 0.15 + rectangle_dict['conus'][-1]), loc='lower left', ncol=2)
    info = plt.axes([0.1, 0.88, 0.9, 0.1])
    info.text(0.9, 0.8, f'Page: {page[0]}/{page[1]}', fontsize=8)
    info.axis('off')

    return figure


def make_grid(rect: List[float], ymin_ymax: List[float], x_params: dict) -> Axes:
    """Generate a grid as a data-less Axes object. The vertical grid is common for all boxes, the horizontal grid is
    described in the input x_params"""
    grid = plt.axes(rect)
    grid.set_ylim(ymin_ymax)
    grid.yaxis.set_major_locator(MultipleLocator(5))
    grid.yaxis.set_minor_locator(MultipleLocator(1))
    grid.yaxis.grid(True, which='minor')
    grid.yaxis.grid(True, which='major', linewidth=2)

    grid.set_xlim([x_params['min'], x_params['max']])
    grid.xaxis.set_major_locator(MultipleLocator(x_params['major_locator']))
    grid.xaxis.set_minor_locator(MultipleLocator(x_params['minor_locator']))
    grid.xaxis.grid(True, which='minor')
    grid.xaxis.grid(True, which='major', linewidth=2)
    return grid


def create_conus_box_multi(rect: List[float], ymin_ymax: List[float], multi_gef_data: List[GEFData]) -> Axes:
    """Set the properties of the conus box in the case where multiple CPTs are plotted on the same page """
    x_params = {
        'min': 0.75,
        'max': 0,
        'major_locator': 0.25,
        'minor_locator': 0.05}
    conus = make_grid(rect, ymin_ymax, x_params)
    conus.set_ylabel('Elevation w.r.t NAP [m]')
    conus.xaxis.set_ticklabels([])

    conus_twiny = conus.twiny()
    conus_twiny.set_xlim([0, 30])
    conus_twiny.xaxis.set_major_locator(MultipleLocator(10))
    conus_twiny.xaxis.set_minor_locator(MultipleLocator(2))
    conus_twiny.tick_params(axis='x', length=5, width=1)
    conus_twiny.set_xlabel('Cone resistance qc [MPa]')

    for gef_data in multi_gef_data:
        conus_twiny.plot(gef_data.qc, [el / 1e3 for el in gef_data.elevation], linewidth=1, label=gef_data.name)

    return conus


def create_friction_ratio_box_multi(rect: List[float], ymin_ymax: List[float], multi_gef_data: List[GEFData]) -> Axes:
    """Set the properties of the friction ratio box in the case where multiple CPTs are plotted on the same page """
    x_params = {
        'min': 10,
        'max': 0,
        'major_locator': 10,
        'minor_locator': 2}
    rf = make_grid(rect, ymin_ymax, x_params)
    rf.yaxis.set_ticklabels([])
    rf.tick_params(axis='y', length=0, width=0)
    rf.xaxis.set_ticklabels([])
    rf.tick_params(axis='x', length=1, width=1)

    rf_twiny = rf.twiny()
    rf_twiny.set_xlim([10, 0])
    rf_twiny.tick_params(axis='x', length=5, width=1, colors='#000000')
    rf_twiny.set_xlabel('Friction ratio [%]', color='#000000')

    for gef_data in multi_gef_data:
        rf_twiny.plot([rf * 100 for rf in gef_data.Rf], [el / 1e3 for el in gef_data.elevation], linewidth=1)

    return rf


def create_info_box(page: Tuple[int, int], gef_data: GEFData) -> Axes:
    """Create a box on the top of the PDF containing information from the headers of the cpt"""
    client = gef_data.client if hasattr(gef_data, 'client') else ' '
    date = gef_data.gef_file_date if hasattr(gef_data, 'gef_file_date') else ' '
    height_system = gef_data.height_system if hasattr(gef_data, 'height_system') else ' '
    norm = gef_data.measurement_standard if hasattr(gef_data, 'measurement_standard') else ' '
    project_name = gef_data.project_name if hasattr(gef_data, 'project_name') else ' '
    cone_type = gef_data.cone_type if hasattr(gef_data, 'cone_type') else ' '
    cone_tip_area = gef_data.cone_tip_area if hasattr(gef_data, 'cone_tip_area') else ' '
    x_coord = gef_data.x_y_coordinates[0] if hasattr(gef_data, 'x_y_coordinates') else ' '
    y_coord = gef_data.x_y_coordinates[1] if hasattr(gef_data, 'x_y_coordinates') else ' '

    rect_info = [0.1, 0.88, 0.7, 0.1]
    info = plt.axes(rect_info)
    info.set_xlim([0, 1])
    info.set_ylim([0, 1])
    info.axis('off')
    info.text(0, 1, f'{gef_data.name}', fontsize=10, fontweight='bold')
    info.text(0, 0.8, f'Client: {client}', fontsize=8)
    info.text(0, 0.7, f'Date: {date}', fontsize=8)
    info.text(0, 0.6, f'height_system: {height_system}', fontsize=8)
    info.text(0, 0.5, f'Norm: {norm}', fontsize=8)
    info.text(0, 0.4, f'Project: {project_name}', fontsize=8)
    info.text(0.4, 0.8, f'Cone number: {cone_type}', fontsize=8)
    info.text(0.4, 0.7, f'Cone area: {cone_tip_area} mm2', fontsize=8)
    info.text(0.8, 0.8, f'X coordinate: {x_coord}', fontsize=8)
    info.text(0.8, 0.7, f'Y coordinate: {y_coord}', fontsize=8)
    info.text(0.8, 0.6, f'Ground level wrt NAP: {gef_data.ground_level_wrt_reference / 1e3} m ', fontsize=8)
    info.text(0.8, 0.5, f'Page: {page[0]}/{page[1]}', fontsize=8)

    return info


def create_conus_box_single(rect: List[float], ymin_ymax: List[float], gef_data: GEFData) -> Axes:
    """Set the properties of the conus box in the case where a single CPT is plotted on one page """
    x_params = {
        'min': 0.75,
        'max': 0,
        'major_locator': 0.25,
        'minor_locator': 0.05}
    conus = make_grid(rect, ymin_ymax, x_params)
    conus.set_ylabel(f'Elevation w.r.t {gef_data.height_system} [m]')
    conus.tick_params(axis='x', length=5, width=1, colors='#DE1D1F')
    conus.plot([Rf * qc for qc, Rf in zip(gef_data.qc, gef_data.Rf)],
               [el / 1e3 for el in gef_data.elevation],
               color='#DE1D1F', linewidth=1)
    conus.set_xlabel('Sleeve friction \N{LATIN SMALL LETTER F}\N{LATIN SUBSCRIPT SMALL LETTER S} [MPa]',
                     color='#DE1D1F')

    conus_twiny = conus.twiny()
    conus_twiny.set_xlim([0, 30])
    conus_twiny.xaxis.set_major_locator(MultipleLocator(10))
    conus_twiny.xaxis.set_minor_locator(MultipleLocator(2))
    conus_twiny.tick_params(axis='x', length=5, width=1, colors='#005DAB')
    conus_twiny.plot(gef_data.qc, [el / 1e3 for el in gef_data.elevation], color='#005DAB',
                     linewidth=1)
    conus_twiny.set_xlabel('Cone resistance qc [MPa]', color='#005DAB')

    # Print on PDF qc values exceeding 30 MPa
    mask = [True if (qc > 30) & (ymin_ymax[0] < el / 1e3 < ymin_ymax[1]) else False for qc, el in
            zip(gef_data.qc, gef_data.elevation)]
    filtered_qc = np.array(gef_data.qc)[mask].tolist()
    filtered_elevation = np.array(gef_data.elevation)[mask].tolist()
    x = filtered_qc
    y = [el / 1e3 for el in filtered_elevation]
    start = -1
    for end in np.where(np.diff(y) < -0.04)[0]:
        if end > start + 1:  # If a section is > 1 index long, find val and plotheight with slice
            maxval = max(x[start + 1:end])
            plotheight = np.average(y[start + 1:end])
        else:
            maxval = x[end]
            plotheight = y[end]
        conus.text(0, plotheight, str(np.round(maxval, decimals=1)), horizontalalignment='left',
                   verticalalignment='center', fontsize=7, color='#005DAB')
        start = end

    conus.set_frame_on(True)
    return conus


def create_verticality_box(rect: List[float], ymin_ymax: List[float], gef_data: GEFData) -> Axes:
    """Create a (blank) box to display the inclination of the CPT. A numerical value is given for every
    vertical tick. Inclination is directly read from the gef file if provided, or calculated if the
    inclinations_n_s and inclination_w_e are provided. Inclinations from the GEFData object are in radians
    but should be displayed in degrees in the plot"""
    verticality = plt.axes(rect)
    verticality.axis('off')
    verticality.set_ylim(ymin_ymax)
    range_elevation = list(np.arange(ymin_ymax[0], ymin_ymax[1], 1))
    # left and right parameters determine which value is returned when asking for x_requested outside x_data domain
    interpolated_inclination = np.interp(range_elevation, [el / 1e3 for el in gef_data.elevation][::-1],
                                         gef_data.inclination[::-1], left=999999, right=999999)

    for el, incl in zip(range_elevation, interpolated_inclination):
        if incl == 999999:  # These values were outside data domain, so do not display an inclination
            continue
        verticality.text(0.5, el, f'{(incl * 180) / pi:.1f}°', horizontalalignment='left',
                         verticalalignment='center', fontsize=7)

    return verticality


def create_friction_ratio_box(rect: List[float], ymin_ymax: List[float], gef_data: GEFData) -> Axes:
    """Set the properties of the friction ratio box in the case where a single CPT is plotted on one page """
    x_params = {
        'min': 10,
        'max': 0,
        'major_locator': 10,
        'minor_locator': 2}
    rf = make_grid(rect, ymin_ymax, x_params)
    rf.yaxis.set_ticklabels([])
    rf.tick_params(axis='y', length=0, width=0, colors='#000000')
    rf.xaxis.set_ticklabels([])
    rf.tick_params(axis='x', length=1, width=1, colors='#000000')

    rf_twiny = rf.twiny()
    rf_twiny.set_xlim([10, 0])
    rf_twiny.tick_params(axis='x', length=5, width=1, colors='#000000')
    rf_twiny.plot([rf * 100 for rf in gef_data.Rf], [el / 1e3 for el in gef_data.elevation],
                  color='#000000',
                  linewidth=1)
    rf_twiny.set_xlabel('Friction ratio [%]', color='#000000')

    # Print on PDF Rf values exceeding 10 %
    mask = [True if (rf * 100 > 10) & (ymin_ymax[0] < el / 1e3 < ymin_ymax[1]) else False for rf, el in
            zip(gef_data.Rf, gef_data.elevation)]
    filtered_rf = np.array(gef_data.Rf)[mask].tolist()
    filtered_elevation = np.array(gef_data.elevation)[mask].tolist()
    x = filtered_rf
    y = [el / 1e3 for el in filtered_elevation]
    start = -1
    for end in np.where(np.diff(y) < -0.04)[0]:
        if end > start + 1:  # If a section is > 1 index long, find val and plotheight with slice
            maxval = max(x[start + 1:end])
            plotheight = np.average(y[start + 1:end])
        else:
            maxval = x[end]
            plotheight = y[end]
        rf.text(0, plotheight, str(100 * np.round(maxval, decimals=2)), horizontalalignment='right',
                verticalalignment='center', fontsize=7, color='#000000')
        start = end

    return rf


def color_coded_cpt_map_points(cpt_models: List[CPT]) -> List[MapPoint]:
    """Function that assigns correct color to CPT based on location wrt. Polyline or exclusion"""
    map_features = []
    for cpt in cpt_models:
        map_features.append(cpt.get_map_point())
    return map_features

