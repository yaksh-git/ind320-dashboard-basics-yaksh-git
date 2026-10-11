"""Page 5 (moved from page 4 in Part 2): data guide and project context."""

import streamlit as st


from dashboard.ui import page_header

page_header("IND320 / DATA GUIDE", "Behind the numbers",
            "A short guide to the sources, areas, measurements and choices used in this project.")
left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("Reservoir areas (NVE)")
    st.markdown("""
    - **EL 1–5:** five electricity price areas (NO1–NO5).
    - **VASS 1–3:** watercourse regions with data. The API also lists VASS4 (Nord-Norge), but it has no measurements.
    - **NO 0:** the total for Norway.

    The long time-series plots use **NO 0** so that a line follows the same area each week.
    The *Reservoir areas* page draws one line per area of the chosen type.
    """)
with right, st.container(border=True):
    st.subheader("Read the units")
    st.markdown("""
    - **Fill level:** a fraction; 0.75 means 75% full.
    - **TWh / MWh:** energy. 1 TWh = 1,000,000 MWh.
    - **Weekly change:** a change of 0.01 means one percentage point.
    - **Date:** the Sunday that ends the ISO week of the measurement.

    The value **0001** in the next-publication-date field means no usable date was supplied.
    """)
with st.container(border=True):
    st.subheader("Where the data come from")
    st.markdown("""
    | Pages | Source | How the app gets it |
    |---|---|---|
    | Home, Data table, Data plot, Reservoir areas | [NVE Magasinstatistikk API](https://biapi.nve.no/magasinstatistikk/swagger/index.html) | Direct API request, cached for six hours |
    | Cross-border flows | [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) | Notebook: API → Cassandra (Spark) → MongoDB; the app reads MongoDB |
    """)
with st.container(border=True):
    st.subheader("About this project")
    st.write("IND320 combines a Jupyter Notebook for analysis and documentation with a Streamlit app. "
             "In Part 1 the app read a fixed CSV snapshot. Part 2 replaces it with NVE's open API and "
             "adds cross-border flows that were prepared with Spark and Cassandra and stored in MongoDB.")
    st.write("The combined numeric view on the plot page uses separate panels and vertical scales, "
             "preserving the original units.")
    st.markdown("[NVE methodology](https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/) · "
                "[ENTSO-E API guide](https://documenter.getpostman.com/view/7009892/2s93JtP3F6) · "
                "[Project repository](https://github.com/yaksh-git/ind320-dashboard-basics-yaksh-git)")
