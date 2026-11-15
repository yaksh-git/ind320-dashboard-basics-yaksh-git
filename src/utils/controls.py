"""Shared controls for the reservoir and analysis pages.

The Reservoir data page shows the download interval (month slider) and the type of area (EL, NO or
VASS). The analysis pages (Fill-level analysis, Weather vs. reservoir, Weather outliers, Forecast)
show the same type of area plus one area of that type, because their methods need a single series.
A click on the Map page chooses the area in the same way (select_area). The Map, Weather vs.
reservoir and Forecast pages also share one time period (period_slider).
The choices are kept in st.session_state, so they follow the user from page to page.
"""

import pandas as pd
import streamlit as st

from src.utils.nve_api import AREA_TYPES, areas_of_type


# Permanent keys: Streamlit keeps these when the user switches page.
INTERVAL_KEY = "reservoir_interval"
AREA_TYPE_KEY = "reservoir_area_type"
AREA_KEY = "reservoir_area"  # {area type: chosen area number}
PERIOD_KEY = "analysis_period"  # (first week, last week) shared by the Map, correlation and forecast
DEFAULT_YEARS = 5  # default interval: the last five years
DEFAULT_PERIOD_YEARS = 8  # default period: the history length that forecast best in the notebook tests
DEFAULT_AREAS = {"EL": 3, "NO": 0, "VASS": 1}  # NO 3 is also the area used in the Part 3 notebook


def _remember(widget_key: str, stored_key: str) -> None:
    """Copy a widget's value to a permanent key (widget keys are removed on page change)."""
    st.session_state[stored_key] = st.session_state[widget_key]


def _remember_area(area_type: str) -> None:
    """Store the chosen area number for one area type (each type has its own select box)."""
    st.session_state[AREA_KEY][area_type] = st.session_state[f"area_widget_{area_type}"]


def area_type_radio() -> str:
    """The shared "Type of area" radio (EL, NO, VASS); return the chosen type."""
    st.session_state.setdefault(AREA_TYPE_KEY, "NO")
    # The stored value is passed as index=, so every page starts from the same choice.
    return st.radio(
        "Type of area", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True,
        index=list(AREA_TYPES).index(st.session_state[AREA_TYPE_KEY]), key="area_type_widget",
        on_change=_remember, args=("area_type_widget", AREA_TYPE_KEY),
    )


def reservoir_controls(months: list[str]) -> tuple[str, str, str]:
    """Show the interval slider and the area-type radio; return (first month, last month, type)."""
    # First visit, or a stored month that no longer exists: fall back to the defaults.
    stored = st.session_state.get(INTERVAL_KEY)
    if not stored or stored[0] not in months or stored[1] not in months:
        st.session_state[INTERVAL_KEY] = (months[-12 * DEFAULT_YEARS], months[-1])

    with st.container(border=True):
        # A value with two items, (start, end), makes Streamlit draw a range slider.
        first, last = st.select_slider(
            "Download interval (months, inclusive)", options=months,
            value=st.session_state[INTERVAL_KEY], key="interval_widget",
            on_change=_remember, args=("interval_widget", INTERVAL_KEY),
        )
        area_type = area_type_radio()
        # Explain why a slider is enough: the API itself cannot filter by date.
        st.caption("NVE's API has no date parameters: the endpoint used here returns the full history. "
                   "The app downloads it once (cached for six hours) and keeps only this interval. "
                   "The interval applies to both tabs on this page; the type of area is shared "
                   "with the analysis pages.")
    return first, last, area_type


def area_names(frame: pd.DataFrame, areas: pd.DataFrame, area_type: str) -> dict[int, str]:
    """Area numbers of one type that have data, with NVE's names (e.g. {3: "NO 3"})."""
    # Built from the data, not from HentOmråder alone: VASS4 is listed there but has no measurements.
    subset = areas_of_type(frame, areas, area_type)[["area_number", "area"]].drop_duplicates()
    return {int(number): name for number, name in zip(subset["area_number"], subset["area"])}


def select_area(area_type: str, area_number: int) -> None:
    """Make one area the chosen area on every page (used by a click on the Map page)."""
    st.session_state.setdefault(AREA_KEY, dict(DEFAULT_AREAS))
    st.session_state[AREA_TYPE_KEY] = area_type
    st.session_state[AREA_KEY][area_type] = area_number


def chosen_area() -> tuple[str, int]:
    """The area that is chosen right now (type, number), without drawing any control."""
    st.session_state.setdefault(AREA_KEY, dict(DEFAULT_AREAS))
    area_type = st.session_state.get(AREA_TYPE_KEY, "NO")
    return area_type, st.session_state[AREA_KEY][area_type]


def area_controls(frame: pd.DataFrame, areas: pd.DataFrame) -> tuple[str, int, str]:
    """Show the shared area-type radio and a select box for one area; return (type, number, name)."""
    st.session_state.setdefault(AREA_KEY, dict(DEFAULT_AREAS))
    area_type = area_type_radio()
    names = area_names(frame, areas, area_type)
    numbers = list(names)
    stored = st.session_state[AREA_KEY].get(area_type)
    # One select box per type (own key), so switching type never leaves an invalid choice behind.
    number = st.selectbox(
        "Area", numbers, format_func=names.get,
        index=numbers.index(stored) if stored in numbers else 0,
        key=f"area_widget_{area_type}", on_change=_remember_area, args=(area_type,),
    )
    return area_type, number, names[number]


def period_slider(weeks: list[pd.Timestamp], label: str = "Time period (weeks ending on Sunday)",
                  key: str = "period_widget") -> tuple[pd.Timestamp, pd.Timestamp]:
    """Range slider over NVE's weeks, shared by several pages; return (first week, last week).

    The Map page colours the areas for this period, Weather vs. reservoir correlates over it and the
    Forecast page trains on it and forecasts from its last week. The default is the last eight years.
    """
    stored = st.session_state.get(PERIOD_KEY)
    if not stored or stored[0] not in weeks or stored[1] not in weeks:
        st.session_state[PERIOD_KEY] = (weeks[-52 * DEFAULT_PERIOD_YEARS], weeks[-1])
    return st.select_slider(
        label, options=weeks, value=st.session_state[PERIOD_KEY], key=key,
        format_func=lambda week: f"{week:%d %b %Y}",
        on_change=_remember, args=(key, PERIOD_KEY),
    )
