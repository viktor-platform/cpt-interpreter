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
from pathlib import Path

import viktor as vkt

from .parametrization import Parametrization
from .soil_layout_conversion_functions import (
    Classification,
    convert_input_table_field_to_soil_layout,
    convert_soil_layout_from_mm_to_meter,
    convert_soil_layout_to_input_table_field,
)
from .visualisation import visualise_cpt


class CPTFileController(vkt.ViktorController):
    label = "CPT File"
    parametrization = Parametrization(width=40)

    def classify_soil_layout(self, params, **kwargs) -> vkt.SetParamsResult:
        """Classify the CPT file when it is first uploaded"""
        if params.classification.get_sample_gef_toggle:
            file = self._get_sample_gef_file()
        else:
            file_resource = params.classification.gef_file
            if not file_resource:
                raise vkt.UserError("Upload and select a GEF file.")
            file = file_resource.file

        cpt_file = vkt.geo.GEFFile(file.getvalue("ISO-8859-1"))
        classification = Classification(params["classification"])
        results = classification.classify_cpt_file(cpt_file)

        return vkt.SetParamsResult(results)

    @staticmethod
    def _get_sample_gef_file():
        gef_file_path = Path(__file__).parent / "sample_gef.GEF"
        return vkt.File.from_path(gef_file_path)

    def download_sample_gef_file(self, **kwargs):
        """Download the sample GEF file."""
        gef_file = self._get_sample_gef_file()
        return vkt.DownloadResult(gef_file, "sample_gef.GEF")

    @vkt.PlotlyAndDataView("CPT interpretation", duration_guess=3)
    def visualize_cpt(self, params, **kwargs) -> vkt.PlotlyAndDataResult:
        """Visualizes the Qc and Rf line plots, the soil layout bar plots and the data of the cpt."""
        fig = visualise_cpt(cpt_params=params)
        data_group = self.get_data_group(params)
        return vkt.PlotlyAndDataResult(fig.to_json(), data=data_group)

    @vkt.MapView("Map", duration_guess=2)
    def visualize_map(self, params, **kwargs) -> vkt.MapResult:
        """Visualize the MapView with the CPT location."""
        headers = params.get("headers")
        if not headers:
            raise vkt.UserError("GEF file has no headers")

        x_coordinate, y_coordinate = headers.x_y_coordinates
        cpt_features = []
        if None not in (x_coordinate, y_coordinate):
            cpt_features.append(vkt.MapPoint.from_geo_point(vkt.GeoPoint.from_rd((x_coordinate, y_coordinate))))
        return vkt.MapResult(cpt_features)

    @staticmethod
    def get_data_group(params) -> vkt.DataGroup:
        """Collect the necessary information from the GEF headers and return a DataGroup with the data"""
        headers = params.get("headers")
        if not headers:
            raise vkt.UserError("GEF file has no headers")

        x_coordinate, y_coordinate = headers.x_y_coordinates
        return vkt.DataGroup(
            ground_level_wrt_reference_m=vkt.DataItem(
                "Ground level", headers.ground_level_wrt_reference_m or -999, suffix="m"
            ),
            ground_water_level=vkt.DataItem("Phreatic level", params.ground_water_level, suffix="m"),
            height_system=vkt.DataItem("Height system", headers.height_system or "-"),
            coordinates=vkt.DataItem(
                "Coordinates",
                "",
                subgroup=vkt.DataGroup(
                    x_coordinate=vkt.DataItem("X-coordinate", x_coordinate or 0, suffix="m"),
                    y_coordinate=vkt.DataItem("Y-coordinate", y_coordinate or 0, suffix="m"),
                ),
            ),
        )

    @staticmethod
    def filter_soil_layout_on_min_layer_thickness(params, **kwargs) -> vkt.SetParamsResult:
        """Remove all layers below the filter threshold."""
        vkt.progress_message("Filtering thin layers from soil layout")

        # Create SoilLayout
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

        return vkt.SetParamsResult({"soil_layout": table_input_soil_layers})

    @staticmethod
    def reset_soil_layout_user(params, **kwargs) -> vkt.SetParamsResult:
        """Place the original soil layout (after parsing) in the table input."""
        vkt.progress_message("Resetting soil layout to original unfiltered result")

        # get the original soil layout from the hidden field
        soil_layout_original = vkt.geo.SoilLayout.from_dict(params.soil_layout_original)

        # convert it to a format for the input table
        table_input_soil_layers = convert_soil_layout_to_input_table_field(
            convert_soil_layout_from_mm_to_meter(soil_layout_original)
        )

        return vkt.SetParamsResult(
            {
                "soil_layout": table_input_soil_layers,
                "bottom_of_soil_layout_user": params.get("bottom_of_soil_layout_user"),
            }
        )
