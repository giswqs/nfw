import os
import ee
import geemap.foliumap as geemap
import streamlit as st


def app():

    st.title("NAIP Imagery for Missouri River Basins")

    col1, col2, col3, col4, col5, col6, col7, _ = st.columns([1.8, 1, 2, 2, 1, 1, 1, 1])

    naip_count = {
        "2003": 26077,
        "2004": 53323,
        "2005": 55570,
        "2006": 62976,
        "2007": 22060,
        "2008": 28334,
        "2009": 47088,
        "2010": 46418,
        "2011": 24892,
        "2012": 37606,
        "2013": 27017,
        "2014": 37896,
        "2015": 42909,
        "2016": 24088,
        "2017": 42936,
        "2018": 27789,
        "2019": 37855,
        "2020": 0,
        "2021": 0,
    }

    Map = geemap.Map(plugin_Draw=True, Draw_export=True)
    with col1:
        basemap = st.selectbox("Select a basemap", geemap.basemaps.keys())
    Map.add_basemap(basemap)

    roi = ee.FeatureCollection("users/giswqs/MRB/NWI_HU8_Boundary_Simplify")
    style = {"color": "0000FF", "width": 2, "fillColor": "00000000"}

    with col2:
        checkbox = st.checkbox("Add NAIP imagery")

    with col5:
        lat = st.text_input("Center latitude", "40")

    with col6:
        lon = st.text_input("Center longitude", "-100")

    with col7:
        zoom = st.text_input("Zoom", "4")

    if checkbox:
        with col3:
            year = st.slider("Select a year", 2003, 2021, 2019)
        naip = ee.ImageCollection("USDA/NAIP/DOQQ")
        naip = naip.filter(ee.Filter.calendarRange(year, year, "year"))
        naip = naip.filterBounds(roi)

        # 2005, 2006, 2007,
        vis_params = {"bands": ["N", "R", "G"]}
        if year in [2005, 2006, 2007]:
            vis_params = {"bands": ["R", "G", "B"]}

        Map.addLayer(naip, vis_params, f"NAIP {year}")

        with col4:
            st.write(f"Number of images: {naip_count[str(year)]}")

    Map.addLayer(roi.style(**style), {}, "MRB")
    Map.set_center(float(lon), float(lat), int(zoom))
    Map.to_streamlit(width=1400, height=700)
