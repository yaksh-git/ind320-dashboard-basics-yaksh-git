"""Front page and instructions for navigating the dashboard."""

import streamlit as st


st.title("Norwegian reservoir dashboard")
st.write(
    "Explore weekly reservoir data using the pages in the sidebar. "
    "The data table summarizes each source column, and the data plot lets you "
    "select a variable and a range of months."
)
st.info("Part 1 uses the local reservoirs.csv file. Later project parts can add a database.")

