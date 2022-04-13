import streamlit as st


def app():
    st.title("Home")

    st.header("Introduction")
    st.markdown(
        "This interactive web app (<https://spatial.utk.edu/nfw>) is dedicated to the Non-floodplain Wetlands (NFW) Project."
    )
    st.markdown(
        """
    - **Project Title**: Evaluating Non-floodplain Wetlands for Flood-Risk Reduction and Nutrient Mediation in the Mississippi River Basin
    - **Start/End Dates**: 10/1/2020 - 3/31/2025
    - **Project Team**: Adnan Rajib (PI), Qiusheng Wu (Co-PI)
    - **Sponsor:** U.S. Army Corps of Engineers, Engineer Research and Development Center (ERDC) | U.S. Environmental Protection Agency (EPA)
    """
    )

    st.header("Study Area")
    st.write(
        "The Mississippi River system ⎼ Upper Mississippi, Ohio, and Missouri  River Basins."
    )

    with st.expander("See source code"):
        with st.echo():

            import ee
            import geemap.foliumap as geemap

            Map = geemap.Map(
                center=(40, -100), zoom=5, plugin_Draw=True, Draw_export=False
            )
            huc2 = ee.FeatureCollection("USGS/WBD/2017/HUC02").filter(
                ee.Filter.inList(
                    "name",
                    ["Upper Mississippi Region", "Missouri Region", "Ohio Region"],
                )
            )
            ROI = ee.FeatureCollection("users/giswqs/MRB/NWI_HU8_Boundary_Simplify")
            Map.add_styled_vector(
                huc2,
                column="huc2",
                palette=["006633", "E5FFCC", "662A00"],
                layer_name="NDH-HU2",
            )
            ROI_style = ROI.style(
                **{"color": "0000FF", "width": 2, "fillColor": "00000000"}
            )
            Map.addLayer(ROI_style, {}, "Study Area")
            Map.add_labels(huc2, "name", draggable=False)

    Map.to_streamlit(width=1400, height=650)
