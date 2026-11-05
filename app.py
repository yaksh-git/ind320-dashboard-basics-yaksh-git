"""Entry point for the seven-page Streamlit app (IND320 Part 3)."""

import os
import tempfile
from pathlib import Path

import streamlit as st


# Matplotlib needs a writable cache when the plot pages load (including on Windows).
mpl_cache = Path(tempfile.gettempdir()) / "ind320-matplotlib"
mpl_cache.mkdir(exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_cache)

st.set_page_config(page_title="Norwegian Reservoir Dashboard", layout="wide")

# Imported here, after MPLCONFIGDIR is set above: ui.py imports Matplotlib, which reads it on import.
from src.utils.ui import setup_ui

setup_ui()
with st.sidebar:
    st.markdown("### Norwegian power data")
    st.caption("IND320 · Part 3\n\nReservoirs from the NVE API, weather from Open-Meteo, "
               "cross-border flows from ENTSO-E.")

# Streamlit renders this page list in the sidebar on every page, grouped by data source.
# Part 3: the reservoir pages come first, followed by the fill-level analysis (same NVE data) and
# the weather page; the type of area is shared by pages 2-5 (src/utils/controls.py).
navigation = st.navigation(
    {
        "Reservoirs (NVE)": [
            st.Page("src/pages/home.py", title="Home", icon="🏠", default=True),
            st.Page("src/pages/data_table.py", title="Data table", icon="📋"),
            st.Page("src/pages/data_plot.py", title="Data plot", icon="📈"),
            st.Page("src/pages/fill_analysis.py", title="Fill-level analysis", icon="〰️"),
        ],
        "Weather (Open-Meteo)": [
            st.Page("src/pages/weather_outliers.py", title="Weather outliers", icon="🌧️"),
        ],
        "Electricity flows (ENTSO-E)": [
            st.Page("src/pages/cross_border.py", title="Cross-border flows", icon="🔌"),
        ],
        "Project": [
            st.Page("src/pages/about.py", title="About", icon="ℹ️"),
        ],
    },
    position="sidebar",
)
navigation.run()
