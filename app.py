"""Entry point for the four-page Streamlit app."""

import os
import tempfile
from pathlib import Path

import streamlit as st


# Matplotlib needs a writable cache when the plot page loads (including on Windows).
mpl_cache = Path(tempfile.gettempdir()) / "ind320-matplotlib"
mpl_cache.mkdir(exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_cache)

st.set_page_config(page_title="Norwegian Reservoir Dashboard", layout="wide")

from ui import setup_ui

setup_ui()
with st.sidebar:
    st.markdown("### Norwegian reservoirs")
    st.caption("IND320 · Part 1\n\nWeekly data, from source to insight.")

# Streamlit renders this page list in the sidebar on every page.
navigation = st.navigation(
    [
        st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        st.Page("pages/data_table.py", title="Data table", icon="📋"),
        st.Page("pages/data_plot.py", title="Data plot", icon="📈"),
        st.Page("pages/about.py", title="About", icon="ℹ️"),
    ],
    position="sidebar",
)
navigation.run()
