import ee
import geemap.foliumap as geemap
import geemap.colormaps as cm
import geopandas as gpd
import streamlit as st


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
       
            - [SRTM](https://developers.google.com/earth-engine/datasets/catalog/CGIAR_SRTM90_V4) (90-m)
            - [NASA SRTM](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003) (30-m)
            - [ASTER GDEM](https://samapriya.github.io/awesome-gee-community-datasets/projects/aster) (30-m)
            - [GMTED](https://developers.google.com/earth-engine/datasets/catalog/USGS_GMTED2010) (232-m)
            - [ALOS DSM](https://developers.google.com/earth-engine/datasets/catalog/JAXA_ALOS_AW3D30_V3_2) (30-m)
            - [GLO-30 DSM](https://samapriya.github.io/awesome-gee-community-datasets/projects/glo30/) (30-m)
            - [FABDEM](https://samapriya.github.io/awesome-gee-community-datasets/projects/fabdem/) (30-m)
            - [NED](https://developers.google.com/earth-engine/datasets/catalog/USGS_3DEP_10m) (10-m)
            - [ESA WorldCover](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v100) (10-m)
            - [ESRI Global Land Cover](https://samapriya.github.io/awesome-gee-community-datasets/projects/esrilc2020/) (10-m)
            - [NLCD](https://developers.google.com/earth-engine/datasets/catalog/USGS_NLCD_RELEASES_2016_REL#description) (30-m)
        
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
        "NLCD 2016": ee.Image("USGS/NLCD_RELEASES/2016_REL/2016").select("landcover"),
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
            "Select land cover datasets", list(landcover_options.keys())
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
                first_dem = st.selectbox("First DEM", dem_options.keys())
                second_dem = st.selectbox("Second DEM", dem_options.keys(), index=1)
                min_max = st.slider("Min/Max for visualization", -100, 100, (-20, 20))
                diff_palette = st.selectbox(
                    "Color palette", palettes, index=palettes.index("coolwarm")
                )

    Map = geemap.Map(
        add_google_map=False,
        plugin_LatLngPopup=False,
        locate_control=True,
        plugin_Draw=True,
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
            if dataset == "NLCD 2016":
                Map.add_legend(title="NLCD Land Cover", builtin_legend="NLCD")
            elif dataset == "ESA WorldCover":
                Map.add_legend(
                    title="ESA Global Land Cover", builtin_legend="ESA_WorldCover"
                )
            elif dataset == "ESRI Global Land Cover":
                Map.add_legend(
                    title="ESRI Global Land Cover", builtin_legend="ESRI_LandCover"
                )

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