"""Entry point for the five-page Streamlit app (IND320 Part 2)."""

import os
import tempfile
from pathlib import Path

import streamlit as st


# Matplotlib needs a writable cache when the plot pages load (including on Windows).
mpl_cache = Path(tempfile.gettempdir()) / "ind320-matplotlib"
mpl_cache.mkdir(exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_cache)

st.set_page_config(page_title="Norwegian Reservoir Dashboard", layout="wide")

from src.utils.ui import setup_ui

setup_ui()
with st.sidebar:
    st.markdown("### Norwegian power data")
    st.caption("IND320 · Part 2\n\nReservoirs from the NVE API, cross-border flows from ENTSO-E.")

# Streamlit renders this page list in the sidebar on every page.
# Part 2 (updated assignment, 12.10): pages 2 and 3 share the download-interval slider and the
# area-type radio; page 4 shows the cross-border flows from MongoDB; About moved to page 5.
navigation = st.navigation(
    [
        st.Page("src/pages/home.py", title="Home", icon="🏠", default=True),
        st.Page("src/pages/data_table.py", title="Data table", icon="📋"),
        st.Page("src/pages/data_plot.py", title="Data plot", icon="📈"),
        st.Page("src/pages/cross_border.py", title="Cross-border flows", icon="🔌"),
        st.Page("src/pages/about.py", title="About", icon="ℹ️"),
    ],
    position="sidebar",
)
navigation.run()
