import streamlit as st


def app():
    st.title("Useful Resources")

    st.header("Data")

    st.markdown(
        """
        - [USGS 3DEP Hydrology Program](https://pubs.usgs.gov/tm/11/b11/tm11b11.pdf)
        - [NASA EarthDEM Project](https://earthdata.nasa.gov/learn/articles/earthdem-available-through-csda): Multi-temporal 2-m DEM

        ![](https://cdn.earthdata.nasa.gov/conduit/upload/18247/Virgin_River__Nevada_2_reduced.jpg)
    
    """
    )
