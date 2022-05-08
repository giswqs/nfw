from gettext import lngettext
import ee
import folium
import geemap.foliumap as geemap
import geemap.colormaps as cm
import geopandas as gpd
import streamlit as st
import plotly.express as px
import pandas as pd
from streamlit_folium import st_folium
from folium import plugins
import leafmap

geemap.ee_initialize()


def app():
    st.title("Analyzing Surface Water Dynamics")
    col1, col2 = st.columns([3, 1])

    Map = geemap.Map(search_control=False, center=[44.96, -100.40], zoom_start=9)
    Map.add_basemap("HYBRID")

    jrc_url = "https://storage.googleapis.com/global-surface-water/tiles2020/occurrence/{z}/{x}/{y}.png"
    Map.add_tile_layer(jrc_url, "JRC Water Occurrence")

    wms_url = (
        url
    ) = "https://hydro.nationalmap.gov/arcgis/services/wbd/MapServer/WMSServer?"
    wms_layers, wms_titles = geemap.get_wms_layers(url, return_titles=True)

    with col2:
        wms_layer = st.selectbox(
            "Select a Watershed Boundary Dataset (WBD):", wms_titles, index=4
        )
        huc_level = wms_layer.split("-")[0].zfill(2)

    Map.add_wms_layer(
        wms_url,
        wms_layers[wms_titles.index(wms_layer)],
        name=wms_layer,
        transparent=True,
    )

    # Map = folium.Map()

    # st.session_state["ROI"] = ee.FeatureCollection(
    #     "users/giswqs/MRB/NWI_HU8_Boundary_Simplify"
    # )

    # ROI_style = st.session_state["ROI"].style(
    #     **{"color": "ff0000", "width": 2, "fillColor": "00000000"}
    # )
    # Map.add_tile_layer(
    #     tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    #     name="Google Satellite",
    #     attribution="Google",
    # )
    # Map.addLayer(ROI_style, {}, "Study Area")

    folium.LayerControl().add_to(Map)
    plugins.Geocoder(collapsed=True, position="topleft").add_to(Map)

    with col1:
        m = st_folium(Map, width=1000)

    if (m is not None) and (m["last_clicked"] is not None):
        with col2:
            st.text("Clicked location:")
            st.write(m["last_clicked"])
            coord = m["last_clicked"]
            lat = coord["lat"]
            lng = coord["lng"]
            roi = ee.Geometry.Point([lng, lat])
            fc = (
                ee.FeatureCollection(f"USGS/WBD/2017/HUC{huc_level}")
                .filterBounds(roi)
                .first()
            )
            with st.expander("Selected HUC:"):
                st.write(fc.toDictionary().getInfo())

            months = st.slider("Select start and end month:", 1, 12, (7, 8))
            method = st.selectbox(
                "Select aggregation method:", ["max", "mean", "median"]
            )

            submit = st.button("Submit")
            if submit:
                dataset = (
                    ee.ImageCollection("JRC/GSW1_3/MonthlyHistory")
                    .filter(ee.Filter.calendarRange(months[0], months[1], "month"))
                    .map(lambda img: img.eq(2).selfMask())
                )

                def cal_area(img):
                    pixel_area = img.multiply(ee.Image.pixelArea()).divide(1e4)
                    img_area = pixel_area.reduceRegion(
                        **{
                            "geometry": fc.geometry(),
                            "reducer": ee.Reducer.sum(),
                            "scale": 1000,
                            "maxPixels": 1e12,
                            "bestEffort": True,
                        }
                    )
                    return img.set({"area": img_area})

                areas = dataset.map(cal_area)
                stats = areas.aggregate_array("area").getInfo()
                values = [item["water"] for item in stats]
                labels = areas.aggregate_array("system:index").getInfo()
                years = [int(label[:4]) for label in labels]
                months = [int(label[5:7]) for label in labels]
                df = pd.DataFrame({"year": years, "month": months, "water": values})
                agg_df = df.groupby(["year"])["water"].agg(method)
                st.dataframe(df)
                leafmap.st_download_button("Download data", df)
                # leafmap.st_download_button("Download data", agg_df)
                st.dataframe(agg_df)
                fig = px.bar(
                    df,
                    x="year",
                    y="water",
                    labels={"year": "Year", "water": "Water area (ha)"},
                    title="Surface Water Dynamics",
                )
                with col1:
                    st.plotly_chart(fig)
