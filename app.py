"""Entry point for the Streamlit app (IND320 Part 4): page config, shared style and the grouped menu."""

import streamlit as st


st.set_page_config(page_title="Norwegian Reservoir Dashboard", layout="wide")

from src.utils.ui import setup_ui  # noqa: E402 (set_page_config must be the first Streamlit call)

setup_ui()
with st.sidebar:
    st.markdown("### Norwegian power data")
    st.caption("IND320 · Part 4\n\nReservoirs from NVE, weather from Open-Meteo, exchange rates from "
               "Norges Bank, cross-border flows from ENTSO-E.")

# Part 4: the menu is grouped by the type of task (see the sketch in the Part 4 notebook).
# Start: overview and the map where the area is chosen; Explore: data and exploratory analysis;
# Anomalies: unusual weather; Forecast: predictions; Electricity: Part 2 flows; Info: documentation.
# Each group has its own colour (src/utils/ui.py), shown in the page header and the active menu entry.
navigation = st.navigation(
    {
        "Start": [
            st.Page("src/pages/home.py", title="Home", icon="🏠", default=True),
            st.Page("src/pages/map.py", title="Map", icon="🗺️"),
        ],
        "Explore": [
            st.Page("src/pages/reservoir_data.py", title="Reservoir data", icon="📋"),
            st.Page("src/pages/fill_analysis.py", title="Fill-level analysis", icon="〰️"),
            st.Page("src/pages/correlation.py", title="Weather vs. reservoir", icon="🔗"),
        ],
        "Anomalies": [
            st.Page("src/pages/weather_outliers.py", title="Weather outliers", icon="🌧️"),
        ],
        "Forecast": [
            st.Page("src/pages/forecast.py", title="Reservoir forecast", icon="🔮"),
        ],
        "Electricity": [
            st.Page("src/pages/cross_border.py", title="Cross-border flows", icon="🔌"),
        ],
        "Info": [
            st.Page("src/pages/about.py", title="About", icon="ℹ️"),
        ],
    },
    position="sidebar",
)
navigation.run()
