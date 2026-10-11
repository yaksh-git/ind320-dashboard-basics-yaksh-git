"""Entry point for the six-page Streamlit app (IND320 Part 2)."""

import os
import tempfile
from pathlib import Path

import streamlit as st


# Matplotlib needs a writable cache when the plot pages load (including on Windows).
mpl_cache = Path(tempfile.gettempdir()) / "ind320-matplotlib"
mpl_cache.mkdir(exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_cache)

st.set_page_config(page_title="Norwegian Reservoir Dashboard", layout="wide")

from dashboard.ui import setup_ui

setup_ui()
with st.sidebar:
    st.markdown("### Norwegian power data")
    st.caption("IND320 · Part 2\n\nReservoirs from the NVE API, cross-border flows from ENTSO-E.")

# Streamlit renders this page list in the sidebar on every page.
# Part 2: page 4 is the new NVE area page, the old page 4 (About) moved to page 5,
# and page 6 reads the cross-border flows from MongoDB.
navigation = st.navigation(
    [
        st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        st.Page("pages/data_table.py", title="Data table", icon="📋"),
        st.Page("pages/data_plot.py", title="Data plot", icon="📈"),
        st.Page("pages/reservoir_areas.py", title="Reservoir areas", icon="💧"),
        st.Page("pages/about.py", title="About", icon="ℹ️"),
        st.Page("pages/cross_border.py", title="Cross-border flows", icon="🔌"),
    ],
    position="sidebar",
)
navigation.run()
