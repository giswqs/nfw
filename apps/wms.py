import ee
import ast
import streamlit as st
import geemap.foliumap as geemap


@st.cache
def get_layers(url):
    options = geemap.get_wms_layers(url)
    return options


def app():
    st.title("ESA 10-m Global Land Cover 2020")
    st.markdown(
        """
    This app is a demonstration of loading Web Map Service (WMS) layers. Simply enter the URL of the WMS service 
    in the text box below and press Enter to retrieve the layers. Go to https://apps.nationalmap.gov/services to find 
    some WMS URLs if needed.
    """
    )

    row1_col1, row1_col2 = st.columns([3, 1.3])
    width = 800
    height = 600
    layers = None

    geemap.ee_initialize()
    roi = ee.FeatureCollection("users/giswqs/MRB/NWI_HU8_Boundary_Simplify")
    style = {
        "color": "000000ff",
        "width": 2,
        "lineType": "solid",
        "fillColor": "00000000",
    }

    with row1_col2:

        esa_landcover = "https://services.terrascope.be/wms/v2"
        url = st.text_input(
            "Enter a WMS URL:", value="https://services.terrascope.be/wms/v2"
        )
        empty = st.empty()

        if url:
            options = get_layers(url)

            default = None
            if url == esa_landcover:
                default = [
                    "WORLDCOVER_2020_S2_TCC",
                    "WORLDCOVER_2020_S2_FCC",
                    "WORLDCOVER_2020_MAP",
                ]
            layers = empty.multiselect(
                "Select WMS layers to add to the map:", options, default=default
            )
            add_legend = st.checkbox("Add a legend to the map", value=True)
            if "WORLDCOVER_2020_MAP" in default:
                legend = str(geemap.builtin_legends["ESA_WorldCover"])
            else:
                legend = ""
            if add_legend:
                legend_text = st.text_area(
                    "Enter a legend as a dictionary {label: color}",
                    value=legend,
                    height=200,
                )

        with row1_col1:
            m = geemap.Map(center=(36.3, 0), zoom=2)

            if layers is not None:
                for layer in layers:
                    m.add_wms_layer(
                        url, layers=layer, name=layer, attribution=" ", transparent=True
                    )
            if add_legend and legend_text:
                legend_dict = ast.literal_eval(legend_text)
                m.add_legend(legend_dict=legend_dict)

            m.addLayer(roi.style(**style), {}, "MRB")
            m.to_streamlit(width, height)
