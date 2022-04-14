import ee
import geemap.foliumap as geemap
import geemap.colormaps as cm
import geopandas as gpd
import streamlit as st
import plotly.express as px
import pandas as pd


@st.cache
def uploaded_file_to_gdf(data):
    import tempfile
    import os
    import uuid

    _, file_extension = os.path.splitext(data.name)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(tempfile.gettempdir(), f"{file_id}{file_extension}")

    with open(file_path, "wb") as file:
        file.write(data.getbuffer())

    if file_path.lower().endswith(".kml"):
        gpd.io.file.fiona.drvsupport.supported_drivers["KML"] = "rw"
        gdf = gpd.read_file(file_path, driver="KML")
    else:
        gdf = gpd.read_file(file_path)

    return gdf


def app():

    st.title("DEM Datasets")

    with st.expander("Click to see the data sources", False):
        markdown = """
        **DEM datasets:**

        - [SRTM](https://developers.google.com/earth-engine/datasets/catalog/CGIAR_SRTM90_V4) (90-m)
        - [NASA SRTM](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003) (30-m)
        - [ASTER GDEM](https://samapriya.github.io/awesome-gee-community-datasets/projects/aster) (30-m)
        - [GMTED](https://developers.google.com/earth-engine/datasets/catalog/USGS_GMTED2010) (232-m)
        - [ALOS DSM](https://developers.google.com/earth-engine/datasets/catalog/JAXA_ALOS_AW3D30_V3_2) (30-m)
        - [GLO-30 DSM](https://samapriya.github.io/awesome-gee-community-datasets/projects/glo30/) (30-m)
        - [FABDEM](https://samapriya.github.io/awesome-gee-community-datasets/projects/fabdem/) (30-m)
        - [NED](https://developers.google.com/earth-engine/datasets/catalog/USGS_3DEP_10m) (10-m)

        **Land cover datasets:**

        - [ESA WorldCover](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v100) (10-m)
        - [ESRI Global Land Cover](https://samapriya.github.io/awesome-gee-community-datasets/projects/esrilc2020/) (10-m)
        - [NLCD](https://developers.google.com/earth-engine/datasets/catalog/USGS_NLCD_RELEASES_2016_REL#description) (30-m)

        **Landform datasets:**

        - [Global ALOS Landforms](https://developers.google.com/earth-engine/datasets/catalog/CSP_ERGo_1_0_Global_ALOS_landforms) (90-m)
        - [Global SRTM Landforms](https://developers.google.com/earth-engine/datasets/catalog/CSP_ERGo_1_0_Global_SRTM_landforms) (90-m)
        - [US NED Landforms](https://developers.google.com/earth-engine/datasets/catalog/CSP_ERGo_1_0_US_landforms) (10-m)
        
        """
        st.markdown(markdown)

    row1_col1, row1_col2 = st.columns([4, 1])

    st.session_state["ROI"] = ee.FeatureCollection(
        "users/giswqs/MRB/NWI_HU8_Boundary_Simplify"
    )

    landcover_options = {
        "ESA WorldCover": ee.ImageCollection("ESA/WorldCover/v100").first(),
        "ESRI Global Land Cover": ee.ImageCollection(
            "projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m"
        ).mosaic(),
        "NLCD 2019": ee.Image("USGS/NLCD_RELEASES/2019_REL/NLCD/2019").select(
            "landcover"
        ),
        "Global ALOS Landforms": ee.Image("CSP/ERGo/1_0/Global/ALOS_landforms").select(
            "constant"
        ),
        "Global SRTM Landforms": ee.Image("CSP/ERGo/1_0/Global/SRTM_landforms").select(
            "constant"
        ),
        "NED Landforms": ee.Image("CSP/ERGo/1_0/US/landforms").select("constant"),
    }

    legend_options = {
        "ESA WorldCover": "ESA_WorldCover",
        "ESRI Global Land Cover": "ESRI_LandCover",
        "NLCD 2019": "NLCD",
        "Global ALOS Landforms": "ALOS_landforms",
        "Global SRTM Landforms": "ALOS_landforms",
        "NED Landforms": "ALOS_landforms",
    }

    dem_options = {
        "STRM": ee.Image("CGIAR/SRTM90_V4"),
        "NASA SRTM": ee.Image("USGS/SRTMGL1_003").select("elevation"),
        "NASA DEM": ee.Image("NASA/NASADEM_HGT/001").select("elevation"),
        "ASTER GDEM": ee.Image("projects/sat-io/open-datasets/ASTER/GDEM"),
        "GMTED": ee.Image("USGS/GMTED2010").select("be75").rename("elevation"),
        "ALOS DEM": ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2")
        .mosaic()
        .select("DSM")
        .rename("elevation"),
        "GLO-30": ee.ImageCollection("projects/sat-io/open-datasets/GLO-30")
        .mosaic()
        .rename("elevation"),
        "FABDEM": ee.ImageCollection("projects/sat-io/open-datasets/FABDEM")
        .mosaic()
        .rename("elevation"),
        "NED": ee.Image("USGS/3DEP/10m"),
    }

    palettes = cm.list_colormaps()

    with row1_col2:
        lc_datasets = st.multiselect(
            "Select landcover/landform datasets", list(landcover_options.keys())
        )
        dem_datasets = st.multiselect("Select DEM datasets", dem_options.keys())
        palette = st.selectbox(
            "Select a palette", palettes, index=palettes.index("terrain")
        )
        dem_min_max = st.slider(
            "Set elevation range", min_value=0, max_value=8000, value=(0, 4000), step=50
        )
        opacity = st.slider("Choose DEM layer opacity", 0.1, 1.0, 0.8)

        with st.expander("Click here to upload an ROI", False):
            upload = st.file_uploader(
                "Upload a GeoJSON, KML or Shapefile (as a zif file) to use as an ROI. 😇👇",
                type=["geojson", "kml", "zip"],
            )

        clip = st.checkbox("Clip to ROI")
        add_hillshade = st.checkbox("Add DEM hillshade")

        add_diff = st.checkbox("Add DEM differencing")
        if add_diff:
            with st.expander("DEM differencing", True):
                first_dem = st.selectbox("First DEM", dem_options.keys(), index=1)
                second_dem = st.selectbox("Second DEM", dem_options.keys(), index=3)
                min_max = st.slider("Min/Max for visualization", -100, 100, (-20, 20))
                diff_palette = st.selectbox(
                    "Color palette", palettes, index=palettes.index("coolwarm")
                )
                reducer = st.selectbox(
                    "Statistics",
                    ["mean", "median", "minimum", "maximum", "std", "sum", "variance"],
                )

    Map = geemap.Map(
        add_google_map=False,
        plugin_LatLngPopup=False,
        locate_control=True,
        plugin_Draw=True,
        Draw_export=True,
    )
    Map.add_basemap("HYBRID")
    Map.add_basemap("TERRAIN")

    if upload:
        gdf = uploaded_file_to_gdf(upload)
        st.session_state["ROI"] = geemap.geopandas_to_ee(gdf, geodesic=False)
        Map.add_gdf(gdf, "ROI")

    if lc_datasets:
        for dataset in lc_datasets:
            if dataset == "ESRI Global Land Cover":
                vis = {
                    "min": 1,
                    "max": 10,
                    "palette": list(geemap.builtin_legends["ESRI_LandCover"].values()),
                }
            elif "Landforms" in dataset:
                vis = {
                    "min": 11,
                    "max": 42,
                    "palette": [
                        "141414",
                        "383838",
                        "808080",
                        "EBEB8F",
                        "F7D311",
                        "AA0000",
                        "D89382",
                        "DDC9C9",
                        "DCCDCE",
                        "1C6330",
                        "68AA63",
                        "B5C98E",
                        "E1F0E5",
                        "a975ba",
                        "6f198c",
                    ],
                }
            else:
                vis = {}
            if clip:
                landcover = landcover_options[dataset].clip(st.session_state["ROI"])
                Map.centerObject(st.session_state["ROI"])
            else:
                landcover = landcover_options[dataset]

            Map.addLayer(
                landcover,
                vis,
                dataset,
            )
            if dataset == "NLCD 2019":
                Map.add_legend(title="NLCD Land Cover", builtin_legend="NLCD")
            elif dataset == "ESA WorldCover":
                Map.add_legend(
                    title="ESA Global Land Cover", builtin_legend="ESA_WorldCover"
                )
            elif dataset == "ESRI Global Land Cover":
                Map.add_legend(
                    title="ESRI Global Land Cover", builtin_legend="ESRI_LandCover"
                )
            elif "Landforms" in dataset:
                Map.add_legend(title="Landforms", builtin_legend="ALOS_landforms")

    if dem_datasets:
        for dataset in dem_datasets:
            if clip:
                dem = dem_options[dataset].clip(st.session_state["ROI"])
                Map.centerObject(st.session_state["ROI"])
            else:
                dem = dem_options[dataset]

            if add_hillshade:

                hillshade = ee.Terrain.hillshade(
                    dem.setDefaultProjection("EPSG:3857"), 315, 45
                )
                Map.addLayer(hillshade, {}, f"{dataset} hillshade")

            vis_params = {
                "min": dem_min_max[0],
                "max": dem_min_max[1],
                "palette": cm.get_palette(palette, 15),
            }
            Map.addLayer(dem, vis_params, dataset, True, opacity)
            Map.add_colorbar(
                vis_params,
                label="Elevation (m)",
            )

    if add_diff:
        diff = dem_options[first_dem].subtract(dem_options[second_dem])
        if clip:
            diff = diff.clip(st.session_state["ROI"])
            Map.centerObject(st.session_state["ROI"])
        Map.addLayer(
            diff,
            {
                "min": min_max[0],
                "max": min_max[1],
                "palette": cm.get_palette(diff_palette, 15),
            },
            f"{first_dem} - {second_dem}",
        )
        Map.add_colorbar(
            {
                "min": min_max[0],
                "max": min_max[1],
                "palette": cm.get_palette(diff_palette, 15),
            },
            label=f"Elevation difference (m): {first_dem} - {second_dem}",
        )

    sinks_30m = ee.FeatureCollection("users/giswqs/MRB/NED_30m_sinks")
    Map.addLayer(sinks_30m, {}, "Depressions (30m)", False)

    sinks_10m = ee.FeatureCollection("users/giswqs/MRB/NED_10m_sinks")
    sinks_10m_style = sinks_10m.style(
        **{"color": "0000ff", "width": 2, "fillColor": "0000ff44"}
    )
    Map.addLayer(sinks_10m_style, {}, "Depressions (10m)", False)

    huc8 = ee.FeatureCollection("USGS/WBD/2017/HUC10").filter(
        ee.Filter.Or(
            ee.Filter.stringStartsWith(**{"leftField": "huc10", "rightValue": "05"}),
            ee.Filter.stringStartsWith(**{"leftField": "huc10", "rightValue": "07"}),
            ee.Filter.stringStartsWith(**{"leftField": "huc10", "rightValue": "10"}),
        )
    )
    Map.addLayer(
        huc8.style(**{"fillColor": "00000000", "width": 1}), {}, "NHD-HUC10", False
    )

    ROI_style = st.session_state["ROI"].style(
        **{"color": "ff0000", "width": 2, "fillColor": "00000000"}
    )
    Map.addLayer(ROI_style, {}, "Study Area")

    with row1_col1:

        Map.to_streamlit(height=650)

        if lc_datasets and add_diff:
            for landcover in lc_datasets:
                lc = landcover_options[landcover]
                if clip:
                    lc = lc.clip(st.session_state["ROI"])
                    region = st.session_state["ROI"].geometry().bounds()
                else:
                    region = ee.Geometry.BBox(-180, -85, 180, 85)

                labels = geemap.builtin_legends[legend_options[landcover]].keys()

                try:
                    df = geemap.image_stats_by_zone(
                        diff,
                        lc,
                        reducer=reducer,
                        region=region,
                        labels=labels,
                    )

                    st.write(
                        f"Statstics by {landcover} - {reducer} of {first_dem} - {second_dem}"
                    )
                    st.dataframe(df)
                except Exception as e:
                    st.error(e)

            hist = diff.reduceRegion(
                **{
                    "reducer": ee.Reducer.histogram(maxBuckets=20),
                    "bestEffort": True,
                    "geometry": region,
                    "scale": 1000,
                }
            ).getInfo()
            x = hist["elevation"]["bucketMeans"]
            y = hist["elevation"]["histogram"]
            hist_df = pd.DataFrame(
                {
                    "Value": x,
                    "Count": y,
                }
            )
            fig = px.bar(
                hist_df, x="Value", y="Count", title="Histogram of Elevation Difference"
            )
            st.write("Histogram of Elevation Difference")
            st.dataframe(hist_df)
            st.plotly_chart(fig)
