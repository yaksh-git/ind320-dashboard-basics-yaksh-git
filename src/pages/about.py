"""Info – About: a guide to the sources, areas, units, menu groups and choices (updated for Part 4)."""

import streamlit as st

from src.utils.ui import page_header


def show_areas_and_units() -> None:
    """Two cards side by side: the NVE area codes and how to read the units."""
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("Reservoir areas (NVE)")
        st.markdown("""
        - **EL 1–5:** five electricity price areas (NO1–NO5).
        - **VASS 1–3:** watercourse regions with data. The API also lists VASS4 (Nord-Norge), but it has no measurements.
        - **NO 0:** the total for Norway.

        The long time-series plot on *Home* uses **NO 0**. On *Reservoir data* you choose the interval
        and the area type and see one line per area. The analysis pages use one area: choose it with
        the selector at the top of the page or by clicking it on the *Map*; the choice follows you
        between pages, as does the time period on the Map, Weather vs. reservoir and Forecast pages.
        """)
    with right, st.container(border=True):
        st.subheader("Read the units")
        st.markdown("""
        - **Fill level:** a fraction; 0.75 means 75% full.
        - **TWh / MWh:** energy. 1 TWh = 1,000,000 MWh.
        - **Weekly change:** a change of 0.01 means one percentage point.
        - **Date:** the Sunday that ends the ISO week of the measurement.
        - **Weather:** hourly in °C, mm or cm per hour and km/h (UTC); weekly as mean °C and mm or cm per week.
        - **pp:** percentage points (a change from 60 % to 65 % is 5 pp).
        - **EUR/NOK:** Norwegian kroner per euro (Norges Bank, business days).

        The value **0001** in the next-publication-date field means no usable date was supplied.
        """)


def show_data_sources() -> None:
    """Which pages use which source, and how the app reaches it."""
    with st.container(border=True):
        st.subheader("Where the data come from")
        st.markdown("""
        | Pages | Source | How the app gets it |
        |---|---|---|
        | Home, Map, Reservoir data, Fill-level analysis, Weather vs. reservoir, Forecast | [NVE Magasinstatistikk API](https://biapi.nve.no/magasinstatistikk/swagger/index.html) | Direct API request, cached for six hours |
        | Weather outliers | [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5, hourly) | Direct API request per area and year, cached; 20 representative, weighted locations from the 1000 random points inside [NVE's area maps](https://atlas.nve.no) |
        | Map, Weather vs. reservoir, Forecast | Open-Meteo (ERA5, daily → weekly) | Notebook (Part 4): 12 representative, weighted locations per area, 2016 onwards, weekly means/sums → MongoDB; the app reads MongoDB |
        | Forecast (exogenous variable) | [Norges Bank exchange rates](https://app.norges-bank.no/query/#/en/) | Direct API request, cached for twelve hours |
        | Map outlines | NVE map services (Part 3 notebook) | GeoJSON file in the repository (`data/regions/areas.geojson`) |
        | Cross-border flows | [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) | Notebook: API → Cassandra (Spark) → MongoDB; the app reads MongoDB |
        """)


def show_project_context() -> None:
    """A short description of the project parts and useful links."""
    with st.container(border=True):
        st.subheader("About this project")
        st.write("IND320 combines a Jupyter Notebook for analysis and documentation with a Streamlit app. "
                 "In Part 1 the app read a fixed CSV snapshot. Part 2 replaces it with NVE's open API and "
                 "adds cross-border flows that were prepared with Spark and Cassandra and stored in MongoDB. "
                 "Part 3 adds hourly weather for the same areas and time-series analysis: outliers (SPC), "
                 "anomalies (LOF), STL decomposition and spectrograms. Part 4 adds a map with area selection, "
                 "sliding window correlation between weather and reservoirs, forecasts with River and "
                 "exchange rates from Norges Bank, and replaces all static plots with interactive Plotly charts.")
        st.write("The menu is grouped by the type of task: Start (overview and map), Explore, Anomalies, "
                 "Forecast, Electricity and Info. Each group has its own colour in the page header and the "
                 "menu. Plots never mix units on one axis; combined views use separate panels.")
        st.markdown("[NVE methodology](https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/) · "
                    "[ENTSO-E API guide](https://documenter.getpostman.com/view/7009892/2s93JtP3F6) · "
                    "[Open-Meteo docs](https://open-meteo.com/en/docs/historical-weather-api) · "
                    "[Project repository](https://github.com/yaksh-git/ind320-dashboard-basics-yaksh-git)")


def render_page() -> None:
    """Draw the page: header, areas and units, data sources and project context."""
    page_header("Info", "Behind the numbers",
                "A short guide to the sources, areas, measurements and choices used in this project.")
    show_areas_and_units()
    show_data_sources()
    show_project_context()


render_page()
