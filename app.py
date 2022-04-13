import streamlit as st
from multiapp import MultiApp
from apps import home, datasets, lidar, naip, planet, resources, water, wms

st.set_page_config(layout="wide")


apps = MultiApp()

# Add all your application here

apps.add_app("Home", home.app)
apps.add_app("Planet Imagery", planet.app)
apps.add_app("NAIP Imagery", naip.app)
apps.add_app("Surface Water Datasets", datasets.app)
apps.add_app("NAIP Water Mapping", water.app)
apps.add_app("ESA 10-m Global Land Cover 2020", wms.app)
apps.add_app("LiDAR Data", lidar.app)
apps.add_app("Useful Resources", resources.app)

# The main app
apps.run()
