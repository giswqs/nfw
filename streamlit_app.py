import streamlit as st
from streamlit_option_menu import option_menu
from apps import (
    datasets,
    dem,
    home,
    lidar,
    naip,
    planet,
    resources,
    timelapse,
    water,
    wms,
)

st.set_page_config(page_title="NFW Project", layout="wide")

# A dictionary of apps in the format of {"App title": "App icon"}
# More icons can be found here: https://icons.getbootstrap.com

apps = [
    {"func": home.app, "title": "Home", "icon": "house"},
    {"func": dem.app, "title": "DEM Datasets", "icon": "building"},
    {"func": planet.app, "title": "Planet Imagery", "icon": "globe"},
    {"func": naip.app, "title": "NAIP Imagery", "icon": "camera"},
    {"func": datasets.app, "title": "Surface Water Datasets", "icon": "moisture"},
    {"func": water.app, "title": "NAIP Water Mapping", "icon": "water"},
    {"func": wms.app, "title": "ESA Global Land Cover", "icon": "map"},
    {"func": lidar.app, "title": "LiDAR Data", "icon": "lightning"},
    {"func": timelapse.app, "title": "Timelapse", "icon": "film"},
    {"func": resources.app, "title": "Useful Resources", "icon": "book"},
]

titles = [app["title"] for app in apps]
icons = [app["icon"] for app in apps]

params = st.experimental_get_query_params()

if "page" in params:
    default_index = int(titles.index(params["page"][0].lower()))
else:
    default_index = 0

with st.sidebar:
    selected = option_menu(
        "Main Menu",
        options=titles,
        icons=icons,
        menu_icon="cast",
        default_index=default_index,
    )

    st.sidebar.title("About")
    st.sidebar.info(
        """
        NFW: <https://nfw.gishub.org>
        Scholar: <https://scholar.gishub.org>
    """
    )


for app in apps:
    if app["title"] == selected:
        app["func"]()
        break
