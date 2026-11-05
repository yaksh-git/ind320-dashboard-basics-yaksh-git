"""Shared controls for the reservoir and analysis pages.

The Data table and Data plot pages show the download interval (month slider) and the type of
area (EL, NO or VASS). The two analysis pages (Fill-level analysis, Weather outliers) show the same
type of area plus one area of that type, because STL, spectrograms and weather downloads need a
single series. The choices are kept in st.session_state, so they follow the user from page to page.
"""

import pandas as pd
import streamlit as st

from src.utils.nve_api import AREA_TYPES, areas_of_type


# Permanent keys: Streamlit keeps these when the user switches page.
INTERVAL_KEY = "reservoir_interval"
AREA_TYPE_KEY = "reservoir_area_type"
AREA_KEY = "reservoir_area"  # {area type: chosen area number}
DEFAULT_YEARS = 5  # default interval: the last five years
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
                   "The interval applies to the Data table and Data plot pages; the type of area "
                   "is shared with the analysis pages.")
    return first, last, area_type


def area_names(frame: pd.DataFrame, areas: pd.DataFrame, area_type: str) -> dict[int, str]:
    """Area numbers of one type that have data, with NVE's names (e.g. {3: "NO 3"})."""
    # Built from the data, not from HentOmråder alone: VASS4 is listed there but has no measurements.
    subset = areas_of_type(frame, areas, area_type)[["area_number", "area"]].drop_duplicates()
    return {int(number): name for number, name in zip(subset["area_number"], subset["area"])}


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
