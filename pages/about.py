"""Data guide and project context; the fourth page can grow in later parts."""

import streamlit as st


from ui import page_header

page_header("IND320 / DATA GUIDE", "Behind the numbers",
            "A short guide to the areas, measurements and choices used in this project.")
left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("One date, nine areas")
    st.markdown("""
    - **EL 1–5:** five electricity price areas.
    - **VASS 1–3:** three watercourse regions.
    - **NO 0:** the total for Norway.

    The time-series plots use **NO 0** so that a line follows the same area each week.
    Area counts use all geographic series in the chosen period.
    """)
with right, st.container(border=True):
    st.subheader("Read the units")
    st.markdown("""
    - **Fill level:** a fraction; 0.75 means 75% full.
    - **TWh:** terawatt-hours, a unit of energy.
    - **Weekly change:** a change of 0.01 means one percentage point.
    - **ISO year / week:** calendar identifiers.

    The value **0001** in the next-publication-date field means no usable date was supplied.
    """)
with st.container(border=True):
    st.subheader("About this project")
    st.write("Part 1 of IND320 combines a Jupyter Notebook for analysis and documentation with a four-page Streamlit app. The app reads a fixed local CSV snapshot and caches it between interactions.")
    st.write("The combined numeric view uses separate panels and vertical scales, preserving the original units. Future project parts can extend this page and replace the CSV with a database.")
    st.markdown("[Course dataset](https://github.com/khliland/ind320/tree/main/D2Dbook/data) · [NVE methodology](https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/) · [Project repository](https://github.com/yaksh-git/ind320-dashboard-basics-yaksh-git)")
