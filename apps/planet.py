import os
import ee
import geemap.foliumap as geemap
import streamlit as st


def app():

    st.title("Planet Imagery for Missouri River Basins")
    col1, col2, col3, _, col4, col5, col6, col7, _ = st.columns(
        [1.8, 0.7, 1, 0.2, 1, 1, 1, 1, 1]
    )

    Map = geemap.Map(plugin_Draw=True, Draw_export=False)
    with col1:
        basemap = st.selectbox("Select a basemap", geemap.basemaps.keys())
    Map.add_basemap(basemap)

    roi = ee.FeatureCollection("users/giswqs/MRB/NWI_HU8_Boundary_Simplify")
    style = {"color": "0000FF", "width": 2, "fillColor": "00000000"}

    with col2:
        ratio = st.radio("Planet imagery", ("Quarterly", "Monthly"))

    with col3:
        year = st.slider("Select a year", 2016, 2022, 2020)

    with col5:
        lat = st.text_input("Center latitude", "40")

    with col6:
        lon = st.text_input("Center longitude", "-100")

    with col7:
        zoom = st.text_input("Zoom", "4")

    if ratio == "Quarterly":
        with col4:
            quarter = st.slider("Select a quarter", 1, 4, 1)
            try:
                Map.add_planet_by_quarter(year, quarter)
            except Exception as e:
                st.error(e)
    else:
        with col4:
            month = st.slider("Select a month", 1, 12, 1)
            try:
                Map.add_planet_by_month(year, month)
            except Exception as e:
                st.error(e)
            # checkbox = st.checkbox("Add Planet imagery")

            # if checkbox:
            #     with col3:
            #         year = st.slider("Select a year", 2003, 2021, 2019)
            #     naip = ee.ImageCollection("USDA/NAIP/DOQQ")
            #     naip = naip.filter(ee.Filter.calendarRange(year, year, "year"))
            #     naip = naip.filterBounds(roi)

            #     # 2005, 2006, 2007,
            #     vis_params = {"bands": ["N", "R", "G"]}
            #     if year in [2005, 2006, 2007]:
            #         vis_params = {"bands": ["R", "G", "B"]}

            #     Map.addLayer(naip, vis_params, f"NAIP {year}")

            #     with col4:
            #         st.write(f"Number of images: {naip_count[str(year)]}")

    huc8 = ee.FeatureCollection("USGS/WBD/2017/HUC08").filter(
        ee.Filter.Or(
            ee.Filter.stringStartsWith(**{"leftField": "huc8", "rightValue": "05"}),
            ee.Filter.stringStartsWith(**{"leftField": "huc8", "rightValue": "07"}),
            ee.Filter.stringStartsWith(**{"leftField": "huc8", "rightValue": "10"}),
        )
    )
    Map.addLayer(huc8.style(**{"fillColor": "00000000"}), {}, "NHD-HUC8", False)

    Map.addLayer(roi.style(**style), {}, "MRB")
    Map.set_center(float(lon), float(lat), int(zoom))
    Map.to_streamlit(width=1400, height=700)
