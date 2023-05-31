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
from pathlib import Path

from munch import Munch, unmunchify
from viktor import File, UserError
from viktor.core import ViktorController, progress_message
from viktor.geo import GEFFile, SoilLayout
from viktor.geometry import GeoPoint
from viktor.result import DownloadResult, SetParametersResult
from viktor.views import (
    DataGroup,
    DataItem,
    MapPoint,
    MapResult,
    MapView,
    PlotlyAndDataResult,
    PlotlyAndDataView,
    WebResult,
    WebView,
)

from .parametrization import CPTFileParametrization
from .soil_layout_conversion_functions import (
    Classification,
    convert_input_table_field_to_soil_layout,
    convert_soil_layout_from_mm_to_meter,
    convert_soil_layout_to_input_table_field,
)
from .visualisation import visualise_cpt


class CPTFileController(ViktorController):
    """Controller class which acts as interface for the Sample entity type."""

    label = "CPT File"
    parametrization = CPTFileParametrization(width=40)
    viktor_enforce_field_constraints = True

    def classify_soil_layout(self, params, **kwargs) -> SetParametersResult:
        """Classify the CPT file when it is first uploaded"""
        if params.classification.get_sample_gef_toggle:
            _file = self._get_sample_gef_file()
        else:
            file_resource = params.classification.gef_file
            if not file_resource:
                raise UserError("Upload and select a GEF file.")
            _file = file_resource.file
        cpt_file = GEFFile(_file.getvalue("ISO-8859-1"))
        classification = Classification(params["classification"])
        results = classification.classify_cpt_file(cpt_file)
        return SetParametersResult(results)

    @staticmethod
    def _get_sample_gef_file():
        gef_file_path = Path(__file__).parent / "sample_gef.GEF"
        return File.from_path(gef_file_path)

    def download_sample_gef_file(self, **kwargs):
        """Download the sample GEF file."""
        gef_file = self._get_sample_gef_file()
        return DownloadResult(gef_file, "sample_gef.GEF")

    @PlotlyAndDataView("CPT interpretation", duration_guess=3)
    def visualize_cpt(self, params: Munch, **kwargs) -> PlotlyAndDataResult:
        """Visualizes the Qc and Rf line plots, the soil layout bar plots and the data of the cpt."""
        fig = visualise_cpt(cpt_params=params)
        data_group = self.get_data_group(params)
        return PlotlyAndDataResult(fig.to_json(), data=data_group)

    @MapView("Map", duration_guess=2)
    def visualize_map(self, params: Munch, **kwargs) -> MapResult:
        """Visualize the MapView with the CPT location."""
        headers = params.get("headers")
        if not headers:
            raise UserError("GEF file has no headers")
        try:
            x_coordinate, y_coordinate = params.x_rd, params.y_rd
        except AttributeError:
            x_coordinate, y_coordinate = headers.x_y_coordinates

        cpt_features = []
        if None not in (x_coordinate, y_coordinate):
            cpt_features.append(MapPoint.from_geo_point(GeoPoint.from_rd((x_coordinate, y_coordinate))))
        return MapResult(cpt_features)

    @staticmethod
    def get_data_group(params: Munch) -> DataGroup:
        """Collect the necessary information from the GEF headers and return a DataGroup with the data"""
        headers = params.get("headers")
        if not headers:
            raise UserError("GEF file has no headers")
        try:
            x_coordinate, y_coordinate = params.x_rd, params.y_rd
        except AttributeError:
            x_coordinate, y_coordinate = headers.x_y_coordinates

        return DataGroup(
            ground_level_wrt_reference_m=DataItem(
                "Ground level", headers.ground_level_wrt_reference_m or -999, suffix="m"
            ),
            ground_water_level=DataItem("Phreatic level", params.ground_water_level, suffix="m"),
            height_system=DataItem("Height system", headers.height_system or "-"),
            coordinates=DataItem(
                "Coordinates",
                "",
                subgroup=DataGroup(
                    x_coordinate=DataItem("X-coordinate", x_coordinate or 0, suffix="m"),
                    y_coordinate=DataItem("Y-coordinate", y_coordinate or 0, suffix="m"),
                ),
            ),
        )

    @staticmethod
    def filter_soil_layout_on_min_layer_thickness(params: Munch, **kwargs) -> SetParametersResult:
        """Remove all layers below the filter threshold."""
        progress_message("Filtering thin layers from soil layout")

        # Create SoilLayout
        bottom_of_soil_layout_user = params.get("bottom_of_soil_layout_user")
        classification = Classification(params.classification)
        soil_layout_user = convert_input_table_field_to_soil_layout(
            bottom_of_soil_layout_user=params["bottom_of_soil_layout_user"],
            soil_layers_from_table_input=params["soil_layout"],
            soils=classification.soil_mapping,
        )
        # filter the layer thickness
        soil_layout_user.filter_layers_on_thickness(
            params.cpt.min_layer_thickness, merge_adjacent_same_soil_layers=True
        )
        # convert to meter, and to the format for the input table
        soil_layout_user = convert_soil_layout_from_mm_to_meter(soil_layout_user)
        table_input_soil_layers = convert_soil_layout_to_input_table_field(soil_layout_user)

        # send it to the parametrisation
        return SetParametersResult({"soil_layout": table_input_soil_layers})

    @staticmethod
    def reset_soil_layout_user(params: Munch, **kwargs) -> SetParametersResult:
        """Place the original soil layout (after parsing) in the table input."""
        progress_message("Resetting soil layout to original unfiltered result")
        # get the original soil layout from the hidden field
        soil_layout_original = SoilLayout.from_dict(unmunchify(params.soil_layout_original))

        # convert it to a format for the input table
        table_input_soil_layers = convert_soil_layout_to_input_table_field(
            convert_soil_layout_from_mm_to_meter(soil_layout_original)
        )
        # send it to the parametrisation
        return SetParametersResult(
            {
                "soil_layout": table_input_soil_layers,
                "bottom_of_soil_layout_user": params.get("bottom_of_soil_layout_user"),
            }
        )

    @WebView(" ", duration_guess=1)
    def final_step(self, params, **kwargs):
        """Initiates the process of rendering the last step."""
        html_path = Path(__file__).parent / "final_step.html"
        with html_path.open() as f:
            html_string = f.read()
        return WebResult(html=html_string)
