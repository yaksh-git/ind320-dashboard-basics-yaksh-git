"""Shared controls for the reservoir pages (Data table and Data plot).

Both pages show the same two controls: the download interval (month slider) and the type
of area (EL, NO or VASS). The choices are kept in st.session_state, so they follow the user
from one page to the other.
"""

import streamlit as st

from src.utils.nve_api import AREA_TYPES


# Permanent keys: Streamlit keeps these when the user switches page.
INTERVAL_KEY = "reservoir_interval"
AREA_TYPE_KEY = "reservoir_area_type"
DEFAULT_YEARS = 5  # default interval: the last five years


def _remember(widget_key: str, stored_key: str) -> None:
    """Copy a widget's value to a permanent key (widget keys are removed on page change)."""
    st.session_state[stored_key] = st.session_state[widget_key]


def reservoir_controls(months: list[str]) -> tuple[str, str, str]:
    """Show the interval slider and the area-type radio; return (first month, last month, type)."""
    # First visit, or a stored month that no longer exists: fall back to the defaults.
    stored = st.session_state.get(INTERVAL_KEY)
    if not stored or stored[0] not in months or stored[1] not in months:
        st.session_state[INTERVAL_KEY] = (months[-12 * DEFAULT_YEARS], months[-1])
    st.session_state.setdefault(AREA_TYPE_KEY, "NO")

    with st.container(border=True):
        # The stored values are passed as value=/index=, so both pages start from the same
        # choice. (value= must be a tuple for Streamlit to draw a range slider with two handles.)
        first, last = st.select_slider(
            "Download interval (months, inclusive)", options=months,
            value=st.session_state[INTERVAL_KEY], key="interval_widget",
            on_change=_remember, args=("interval_widget", INTERVAL_KEY),
        )
        area_type = st.radio(
            "Type of area", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True,
            index=list(AREA_TYPES).index(st.session_state[AREA_TYPE_KEY]), key="area_type_widget",
            on_change=_remember, args=("area_type_widget", AREA_TYPE_KEY),
        )
        # Explain why a slider is enough: the API itself cannot filter by date.
        st.caption("NVE's API has no date parameters: every request returns the full history. "
                   "The app downloads it once (cached for six hours) and keeps only this interval. "
                   "The choices apply to both the Data table and the Data plot page.")
    return first, last, area_type
