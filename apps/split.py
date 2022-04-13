import ee
import folium
import geemap.colormaps as cm
import pandas as pd
import streamlit as st
import geemap.foliumap as geemap
import folium.plugins as plugins
from .data_dict import DATA


def app():

    st.title("Split-panel Map")
    # df = pd.read_csv("data/scotland_xyz.tsv", sep="\t")
    basemaps = geemap.basemaps
    names = list(DATA.keys()) + list(basemaps.keys())
    palettes = cm.list_colormaps()

    col1, col1a, col2, col2a, col3, col4, col5, col6 = st.columns(
        [2, 2, 2, 2, 1, 1, 1, 1.5]
    )
    with col1:
        left_name = st.selectbox(
            "Select the left layer",
            names,
            index=names.index("TERRAIN"),
        )

    with col1a:
        left_palette = st.selectbox(
            "Select the left colormap",
            palettes,
            index=palettes.index("terrain"),
        )

    with col2:
        right_name = st.selectbox(
            "Select the right layer",
            names,
            index=names.index("HYBRID"),
        )
    with col2a:
        right_palette = st.selectbox(
            "Select the right colormap",
            palettes,
            index=palettes.index("gist_earth"),
        )

    with col3:
        # lat = st.slider('Latitude', -90.0, 90.0, 55.68, step=0.01)
        lat = st.text_input("Latitude", "40")

    with col4:
        # lon = st.slider('Longitude', -180.0, 180.0, -2.98, step=0.01)
        lon = st.text_input("Longitude", "-100")

    with col5:
        # zoom = st.slider('Zoom', 1, 24, 6, step=1)
        zoom = st.text_input("Zoom", "4")

    # with col6:
    #     checkbox = st.checkbox("Add OS 25 inch")

    m = geemap.Map(
        center=[float(lat), float(lon)],
        zoom=int(zoom),
        locate_control=True,
        draw_control=False,
        measure_control=False,
    )
    measure = plugins.MeasureControl(position="bottomleft", active_color="orange")
    measure.add_to(m)

    if left_name in basemaps:
        left_layer = basemaps[left_name]
    else:
        data = DATA[left_name]
        left_layer = geemap.ee_tile_layer(data["id"], data["vis"], left_name)

    if right_name in basemaps:
        right_layer = basemaps[right_name]
    else:
        data = DATA[right_name]
        right_layer = geemap.ee_tile_layer(data["id"], data["vis"], right_name)

    # if checkbox:
    #     for index, name in enumerate(names):
    #         if "OS 25 inch" in name:
    #             m.add_tile_layer(
    #                 links[index], name, attribution="National Library of Scotland"
    #             )

    if left_name == right_name:
        st.error("Please select different layers")
    m.split_map(left_layer, right_layer)

    st.session_state["ROI"] = ee.FeatureCollection(
        "users/giswqs/MRB/NWI_HU8_Boundary_Simplify"
    )
    ROI_style = st.session_state["ROI"].style(
        **{"color": "ff0000", "width": 2, "fillColor": "00000000"}
    )
    m.addLayer(ROI_style, {}, "Study Area")

    m.to_streamlit(height=600)
