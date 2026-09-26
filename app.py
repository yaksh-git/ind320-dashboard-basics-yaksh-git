"""Entry point for the four-page Streamlit app."""

import streamlit as st


st.set_page_config(page_title="Norwegian Reservoir Dashboard", layout="wide")

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

