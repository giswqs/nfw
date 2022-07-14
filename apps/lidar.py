import ee
import folium
import streamlit as st
import geemap.foliumap as geemap


def app():
    st.title("LiDAR Data")

    options = ["USGS 3DEP", "USGS 3DEP Hillshade", "USGS 3DEP with NHD", "North Dakota"]
    option = st.selectbox("Select an application", options)

    if option == "USGS 3DEP":

        Map = geemap.Map(center=[40, -100], zoom=4)

        url = "https://index.nationalmap.gov/arcgis/services/3DEPElevationIndex/MapServer/WMSServer"
        Map.add_wms_layer(url, "30", "USGS 3DEP")

        dataset = ee.ImageCollection("USGS/3DEP/1m")
        visualization = {
            "min": 0,
            "max": 3000,
            "palette": "terrain",
        }
        left_layer = geemap.ee_tile_layer(dataset, visualization, "3DEP GEE")
        # mosaic = dataset.mosaic().setDefaultProjection("EPSG:3857")
        # left_layer = geemap.ee_tile_layer(ee.Terrain.hillshade(mosaic), {}, "3DEP GEE")

        Map.split_map(left_layer, left_layer)
        Map.to_streamlit(height=650)

    elif option == "USGS 3DEP Hillshade":

        Map = geemap.Map(center=[40, -100], zoom=4)

        dataset = ee.ImageCollection("USGS/3DEP/1m")
        dataset2 = ee.Image("USGS/3DEP/10m")

        mosaic = dataset.mosaic().setDefaultProjection("EPSG:3857")
        left_layer = geemap.ee_tile_layer(
            ee.Terrain.hillshade(mosaic), {}, "3DEP 1-m hillshade"
        )

        # Map.addLayer(ee.Terrain.hillshade(dataset2), {}, "3DEP 10-m hillshade")
        Map.addLayer(geemap.blend(dataset2), {}, "3DEP 10-m hillshade")
        Map.split_map(left_layer, left_layer)
        Map.to_streamlit(height=650)

    elif option == "USGS 3DEP with NHD":

        col1, col2 = st.columns([5, 1])

        fc = ee.FeatureCollection("TIGER/2018/States")
        states = fc.aggregate_array("NAME").getInfo()
        states.sort()

        NHD_options = [
            "NHDArea",
            "NHDFlowline",
            "NHDLine",
            "NHDWaterbody",
            "NHDPoint",
            "NHDPointEventFC",
            "NHDLineEventFC",
            "NHDAreaEventFC",
            "WBDHU2",
            "WBDHU4",
            "WBDHU6",
            "WBDHU8",
            "WBDHU10",
            "WBDHU12",
            "WBDHU14",
            "WBDHU16",
            "WBDLine",
        ]

        with col2:
            state = st.selectbox(
                "Select a state", states, index=states.index("Nebraska")
            )
            selected_fc = fc.filter(ee.Filter.eq("NAME", state))

            name = selected_fc.first().get("STUSPS").getInfo()

            add_jrc = st.checkbox("Add JRC Water Occurrence")

            add_nwi = st.checkbox("Add NWI datasets")

            datasets = st.multiselect("Select NHD datasets", NHD_options)

            if datasets:

                color = st.color_picker("Select an outline color")
                fill_color = st.color_picker("Select a fill color")
                opacity = st.slider("Select a fill opacity", 0.0, 1.0, 0.5)

        Map = geemap.Map(center=[40, -100], zoom=4)

        Map.add_basemap("HYBRID")

        dataset = ee.ImageCollection("USGS/3DEP/1m")
        dataset2 = ee.Image("USGS/3DEP/10m")

        Map.addLayer(geemap.blend(dataset2), {}, "3DEP 10-m hillshade")

        mosaic = dataset.mosaic().setDefaultProjection("EPSG:3857")
        Map.addLayer(ee.Terrain.hillshade(mosaic), {}, "3DEP 1-m hillshade")
        style = {"color": "ffff00", "fillColor": "00000000"}
        Map.center_object(selected_fc)

        if add_nwi:
            nwi_id = f"projects/sat-io/open-datasets/NWI/wetlands/{name}_Wetlands"
            nwi_fc = ee.FeatureCollection(nwi_id)

            names = [
                "Freshwater Forested/Shrub Wetland",
                "Freshwater Emergent Wetland",
                "Freshwater Pond",
                "Estuarine and Marine Wetland",
                "Riverine",
                "Lake",
                "Estuarine and Marine Deepwater",
                "Other",
            ]

            colors = [
                "#008837",
                "#7FC31C",
                "#688CC0",
                "#66C2A5",
                "#0190BF",
                "#13007C",
                "#007C88",
                "#B28653",
            ]
            color_dict = ee.Dictionary(dict(zip(names, colors)))

            nwi_fc = nwi_fc.map(
                lambda f: f.set(
                    {
                        "style": {
                            "width": 1,
                            "color": "00000088",
                            "fillColor": ee.String(
                                color_dict.get(f.get("WETLAND_TY"))
                            ).cat("99"),
                        }
                    }
                )
            )
            Map.addLayer(nwi_fc.style(**{"styleProperty": "style"}), {}, "NWI")
            Map.add_legend(title="NWI Wetland Type", builtin_legend="NWI")

        prefix = f"projects/sat-io/open-datasets/NHD/NHD_{name}/"

        for dataset in datasets:
            try:
                data = ee.FeatureCollection(f"{prefix}{dataset}")

                data_style = {
                    "color": color[1:],
                    "fillColor": fill_color[1:] + hex(int(opacity * 255))[2:].zfill(2),
                }

                Map.addLayer(data.style(**data_style), {}, dataset)
            except Exception as e:
                with col2:
                    st.error(f"dataset {dataset} not found")

        Map.addLayer(selected_fc.style(**style), {}, state)

        with col1:
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
