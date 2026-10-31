"""Page 5 – Weather outliers: SPC outliers and LOF anomalies in hourly ERA5 weather for one area.

The area comes from the shared controls (src/utils/controls.py), the same type of area as on the
reservoir pages; the year is chosen on this page. The weather is downloaded directly from
Open-Meteo when the page needs it (src/utils/weather_api.py) and cached, so there is no separate
download page. Each tab has its own variable and parameters and shows the plot and its statistics.
"""

from datetime import date

import pandas as pd
import streamlit as st

from src.utils.analysis import lof_anomalies, plot_lof, plot_spc, spc_outliers
from src.utils.controls import area_controls
from src.utils.nve_api import load_areas, load_data, nve_or_stop
from src.utils.ui import chart_style, page_header, show_figure
from src.utils.weather_api import FIRST_YEAR, N_LOCATIONS, VARIABLES, weather_or_stop


DEFAULT_YEAR = 2024  # the year analysed in the Part 3 notebook
LOF_NEIGHBOURS = 48  # two days of hours: each hour is compared with about two days around it


def choose_year() -> int:
    """Select box with every complete year from the start of NVE's statistics to last year."""
    years = list(range(FIRST_YEAR, date.today().year))  # the current year is not complete yet
    return st.selectbox("Year", years, index=years.index(DEFAULT_YEAR), key="weather_year")


def choose_variable(default: str, key: str) -> str:
    """Select box with the downloaded weather variables; return the column name."""
    names = list(VARIABLES)
    return st.selectbox("Variable", names, index=names.index(default), key=key,
                        format_func=lambda name: VARIABLES[name][0])


def show_metrics(cards: list[tuple[str, str]]) -> None:
    """A row of st.metric cards from (label, value) pairs."""
    for column, (label, value) in zip(st.columns(len(cards)), cards):
        column.metric(label, value)


# ---- Tab 1: outliers with Statistical Process Control ----

def show_spc_statistics(result: pd.DataFrame, sd: float, unit: str) -> None:
    """Key numbers and a table of the outliers, the largest deviation first."""
    outliers = result.loc[result["outlier"]]
    show_metrics([("Hours", f"{len(result):,}"), ("Outliers", f"{len(outliers):,}"),
                  ("Share of hours", f"{len(outliers) / len(result):.1%}"),
                  ("Robust std. dev.", f"{sd:.3g} {unit}")])
    with st.expander(f"Table of the {len(outliers):,} outliers"):
        table = (outliers.sort_values("satv", key=abs, ascending=False)
                 [["value", "satv", "lower", "upper"]]
                 .rename(columns={"value": f"Value ({unit})", "satv": "SATV", "lower": "Lower limit",
                                  "upper": "Upper limit"}).rename_axis("Time (UTC)"))
        st.dataframe(table.round(3), width="stretch")


def show_spc(weather: pd.DataFrame, title_suffix: str) -> None:
    """SPC tab: variable, DCT cut-off and number of standard deviations, then plot and statistics."""
    left, middle, right = st.columns(3)
    with left:
        variable = choose_variable("precipitation", key="spc_variable")
    cutoff = middle.slider("DCT cut-off (cycles per year)", 1, 52, 12,
                           help="Slower variations than this count as seasonal and are removed. 12 ≈ monthly.")
    n_sd = right.slider("Number of robust standard deviations", 1.0, 6.0, 3.0, step=0.5)
    label, unit = VARIABLES[variable]
    result, sd = spc_outliers(weather[variable], cutoff, n_sd)
    show_figure(plot_spc(result, label, unit, f"{label} with SPC limits ±{n_sd:g} sd, {title_suffix}"))
    show_spc_statistics(result, sd, unit)
    st.caption("A DCT high-pass filter removes the seasonal level; the rest is the seasonally adjusted "
               "variation (SATV). The limits are the median ± n robust standard deviations (MAD × 1.4826) "
               "of the SATV, added back to the seasonal level. For precipitation the lower limit is "
               "below 0 and can never be crossed.")


# ---- Tab 2: anomalies with the Local Outlier Factor ----

def show_lof_statistics(result: pd.DataFrame, unit: str) -> None:
    """Key numbers and a table of the anomalies, the strongest first."""
    anomalies = result.loc[result["anomaly"]]
    show_metrics([("Hours", f"{len(result):,}"), ("Anomalies", f"{len(anomalies):,}"),
                  ("Share of hours", f"{len(anomalies) / len(result):.1%}"),
                  ("Mean of the year", f"{result['value'].mean():.2f} {unit}")])
    with st.expander(f"Table of the {len(anomalies):,} anomalies"):
        table = (anomalies.sort_values("lof_score", ascending=False)[["value", "lof_score"]]
                 .rename(columns={"value": f"Value ({unit})", "lof_score": "LOF score"})
                 .rename_axis("Time (UTC)"))
        st.dataframe(table.round(3), width="stretch")


def show_lof(weather: pd.DataFrame, title_suffix: str) -> None:
    """LOF tab: variable and proportion of anomalies, then plot and statistics."""
    left, right = st.columns(2)
    with left:
        variable = choose_variable("temperature_2m", key="lof_variable")
    # The slider works in percent; LocalOutlierFactor wants a fraction (1 % = 0.01).
    proportion = right.slider("Proportion of anomalies (%)", 0.5, 5.0, 1.0, step=0.5, format="%.1f") / 100
    label, unit = VARIABLES[variable]
    result = lof_anomalies(weather[variable], proportion, LOF_NEIGHBOURS)
    show_figure(plot_lof(result, label, unit, f"{label} with LOF anomalies ({proportion:.1%}), "
                                              f"{title_suffix}"))
    show_lof_statistics(result, unit)
    st.caption(f"Each hour is described by its time and its value (both standardised). LOF compares the "
               f"density around an hour with that of its {LOF_NEIGHBOURS} nearest neighbours, so an hour "
               "is anomalous when its value does not fit the hours around it.")


def show_data_source() -> None:
    """Expander that documents where the weather on this page comes from."""
    with st.expander("About the data on this page"):
        st.markdown(f"""
        - **Source:** [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api),
          model **ERA5** (reanalysis on a 0.25° grid, about 28 × 15 km in Norway), hourly values in UTC.
        - **Locations:** the Part 3 notebook drew 1000 random locations on land inside each area, using
          NVE's polygons for the price areas and NVE regions (east = RS + RØ, north = RM + RN).
          The app downloads {N_LOCATIONS} of them (one per ERA5 grid cell) and shows the **mean per hour**.
          All 1000 would use most of Open-Meteo's free daily quota.
        - **Caching:** one download per area and year; it is reused until the app restarts.
        """)


def render_page() -> None:
    """Draw the page: area and year, then the SPC and LOF tabs and the data-source expander."""
    chart_style()
    page_header("IND320 / WEATHER", "Weather outliers",
                "Find unusual hours in the weather of a reservoir area, with SPC and the Local Outlier Factor.")
    frame = nve_or_stop(load_data)   # the area list follows the reservoir data
    areas = nve_or_stop(load_areas)
    with st.container(border=True):
        left, right = st.columns([3, 1])
        with left:
            area_type, number, name = area_controls(frame, areas)
        with right:
            year = choose_year()
        st.caption(f"Weather is the hourly mean of {N_LOCATIONS} random locations inside {name}, "
                   "downloaded from Open-Meteo for the chosen year. The type of area is shared with "
                   "the other pages.")
    weather = weather_or_stop(area_type, number, year)
    title_suffix = f"{name} {year}"

    spc_tab, lof_tab = st.tabs(["Outlier / SPC", "Anomaly / LOF"])
    with spc_tab:
        show_spc(weather, title_suffix)
    with lof_tab:
        show_lof(weather, title_suffix)
    show_data_source()


render_page()
