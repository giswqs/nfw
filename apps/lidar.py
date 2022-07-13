import ee
import folium
import streamlit as st
import geemap.foliumap as geemap


def app():
    st.title("LiDAR Data")

    options = ["USGS 3DEP", "North Dakota"]
    option = st.selectbox("Select an application", options)

    if option == "USGS 3DEP":

        Map = geemap.Map(center=[40, -100], zoom=4)

        url = "https://index.nationalmap.gov/arcgis/services/3DEPElevationIndex/MapServer/WMSServer"
        Map.add_wms_layer(url, "30", "USGS 3DEP")

        dataset = ee.ImageCollection("USGS/3DEP/1m")
        visualization = {
            "min": 0,
            "max": 3000,
            "palette": [
                "3ae237",
                "b5e22e",
                "d6e21f",
                "fff705",
                "ffd611",
                "ffb613",
                "ff8b13",
                "ff6e08",
                "ff500d",
                "ff0000",
                "de0101",
                "c21301",
                "0602ff",
                "235cb1",
                "307ef3",
                "269db1",
                "30c8e2",
                "32d3ef",
                "3be285",
                "3ff38f",
                "86e26f",
            ],
        }
        left_layer = geemap.ee_tile_layer(dataset, visualization, "3DEP GEE")

        Map.split_map(left_layer, left_layer)
        Map.to_streamlit(height=650)

    elif option == "North Dakota":

        st.markdown(
            """
            List of LiDAR data:
            - [ND LiDAR Dissemmination MapService](https://lidar.dwr.nd.gov): James River Basin LiDAR Phase 6; 7702 files, 61 GB; 120 GB unzipped; 248 GB mosaic.
        """
        )

        row1_col1, row1_col2 = st.columns([3, 1])
        width = 800
        height = 600
        layers = None

        Map = geemap.Map()
        Map.add_basemap("TERRAIN")

        datasets = {
            "ND - James River Basin LiDAR Phase 1": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverPh1QL3"
            ),
            "ND - James River Basin LiDAR Phase 2": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverPh2QL3"
            ),
            "ND - James River Basin LiDAR Phase 3": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverPh3QL3"
            ),
            "ND - James River Basin LiDAR Phase 4": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverPh4QL3"
            ),
            "ND - James River Basin LiDAR Phase 5": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverPh5QL3"
            ),
            "ND - James River Basin LiDAR Phase 6": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverPh6QL3"
            ),
            "ND - James River Basin LiDAR QL2": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARJamesRiverQL2"
            ),
            "ND - Kidder County LiDAR": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARKidderCnty2015QL2"
            ),
            "ND - McKenzie County LiDAR 2014": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARMcKenzieCnty2014QL2"
            ),
            "ND - Red River Basin Mapping Initialive 2008-2010": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARRedRiverQL3"
            ),
            "ND - Stark County LiDAR 2016": ee.FeatureCollection(
                "users/giswqs/MRB/ND_IndexLiDARStarkCnty2016QL3"
            ),
        }

        roi = ee.FeatureCollection("users/giswqs/MRB/NWI_HU8_Boundary_Simplify")
        style = {
            "color": "0000ffff",
            "width": 2,
            "lineType": "solid",
            "fillColor": "00000000",
        }

        with row1_col2:

            add_nd_data = st.checkbox("Add North Dakota LiDAR Data Index")
            options = list(datasets.keys())
            default = None
            if add_nd_data:
                default = options[:]

            data = st.multiselect("Select a dataset", options, default=default)
            for d in data:
                Map.addLayer(datasets[d], {}, d)

        # url = "https://elevation.nationalmap.gov/arcgis/services/3DEPElevation/ImageServer/WMSServer?"
        # Map.add_wms_layer(
        #     url,
        #     layers="3DEPElevation:Hillshade Elevation Tinted",
        #     name="USGS 3DEP Elevation",
        #     format="image/png",
        #     transparent=True,
        # )

        Map.addLayer(roi.style(**style), {}, "MRB")

        with row1_col1:
            Map.to_streamlit(width, height)
