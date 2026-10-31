"""Page 4 – Fill-level analysis: STL decomposition and spectrogram of one area's weekly fill level.

The area is chosen with the shared controls at the top (src/utils/controls.py); the type of area
is the same radio as on the Data table and Data plot pages. Each tab has its own parameters.
Both methods need many years of data, so the page uses the full weekly history from the NVE API.
"""

import pandas as pd
import streamlit as st

from src.utils.analysis import WEEKS_PER_YEAR, plot_spectrogram, plot_stl, spectrogram_db, stl_parts
from src.utils.controls import area_controls
from src.utils.nve_api import load_areas, load_data, nve_or_stop
from src.utils.ui import chart_style, page_header, show_figure


def fill_series(frame: pd.DataFrame, area_type: str, area_number: int) -> pd.Series:
    """Weekly fill level of one area over the full history, on a regular 7-day index."""
    rows = frame.loc[(frame["area_type"] == area_type) & (frame["area_number"] == area_number)]
    # asfreq inserts a missing week as NaN, so every step is exactly one week (STL and spectrogram need that).
    return rows.set_index("date")["fill_level"].sort_index().asfreq("7D")


def show_stl_statistics(parts: pd.DataFrame) -> None:
    """Three key numbers of the decomposition, in percentage points of fill level."""
    last_year = parts["Seasonal"].iloc[-WEEKS_PER_YEAR:]
    cards = [
        ("Seasonal swing (last year)", f"{(last_year.max() - last_year.min()) * 100:.0f} pp"),
        ("Trend range", f"{parts['Trend'].min():.0%} – {parts['Trend'].max():.0%}"),
        ("Remainder, std. dev.", f"{parts['Remainder'].std() * 100:.1f} pp"),
    ]
    for column, (label, value) in zip(st.columns(3), cards):
        column.metric(label, value)


def show_stl(series: pd.Series, name: str) -> None:
    """STL tab: the three parameters, the four-panel plot and its key numbers."""
    left, middle, right = st.columns(3)
    seasonal = left.slider("Seasonal smoother (weeks, odd)", 7, 51, 13, step=2,
                           help="Longer = the yearly pattern may change more slowly between years.")
    # statsmodels needs an odd trend length that is longer than the 52-week period.
    trend = middle.slider("Trend smoother (weeks, odd)", 53, 261, 105, step=2,
                          help="Longer = a smoother trend. 105 weeks ≈ two years.")
    robust = right.toggle("Robust fitting", value=True,
                          help="Gives unusual weeks less weight when the trend and season are estimated.")
    parts = stl_parts(series, seasonal, trend, robust)
    show_figure(plot_stl(parts, f"STL of fill level, {name} (seasonal={seasonal}, trend={trend}, "
                                f"robust={robust})"))
    show_stl_statistics(parts)
    st.caption("Observed = trend + seasonal + remainder. Near both ends the trend is less reliable, "
               "because LOESS only has data on one side. pp = percentage points.")


def show_spectrogram(series: pd.Series, name: str) -> None:
    """Spectrogram tab: window length and overlap, then the colour map."""
    left, right = st.columns(2)
    window = left.slider("Window length (weeks)", 26, 260, 104, step=2,
                         help="Long windows separate frequencies better; short windows follow time better.")
    overlap_share = right.slider("Overlap between windows (%)", 0, 90, 75, step=5)
    overlap = int(window * overlap_share / 100)  # SciPy wants the overlap as a number of weeks
    show_figure(plot_spectrogram(*spectrogram_db(series, window, overlap),
                                 f"Spectrogram of fill level, {name} (window {window} weeks, "
                                 f"overlap {overlap} weeks)"))
    st.caption(f"Window {window} weeks ≈ {window / WEEKS_PER_YEAR:.1f} years. The bright band at "
               "1 cycle per year is the yearly fill-and-draw-down cycle; bands at 2 and 3 are its harmonics.")


def render_page() -> None:
    """Draw the page: area choice, then the STL and spectrogram tabs."""
    chart_style()
    page_header("IND320 / TIME-SERIES ANALYSIS", "Fill-level analysis",
                "Split the weekly reservoir fill level into trend and season, and see which cycles dominate.")
    frame = nve_or_stop(load_data)   # full history, cached (src/utils/nve_api.py)
    areas = nve_or_stop(load_areas)  # area names (HentOmråder)
    with st.container(border=True):
        area_type, number, name = area_controls(frame, areas)
        st.caption("The type of area is shared with the other pages. Both methods use the full weekly "
                   "history from NVE's API, because they need many years.")
    series = fill_series(frame, area_type, number)
    st.caption(f"{name}: {series.notna().sum():,} weeks, {series.index.min():%d %b %Y} to "
               f"{series.index.max():%d %b %Y}.")

    stl_tab, spectrogram_tab = st.tabs(["STL", "Spectrogram"])
    with stl_tab:
        show_stl(series, name)
    with spectrogram_tab:
        show_spectrogram(series, name)


render_page()
