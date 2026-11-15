"""Explore – Weather vs. reservoir: sliding window correlation between a weather property and the reservoirs.

The Streamlit version of the sliding window correlation from the course: the correlation between
two weekly series is computed in a window that slides along the time axis, with the weather shifted
by a chosen lag. A positive lag compares the reservoir now with the weather some weeks earlier
(for example snowfall in winter and the fill-level change at snowmelt).
The area and the time period are shared with the other pages (Map, Forecast); the weather property,
reservoir variable, lag and window are local choices on this page.
"""

import pandas as pd
import streamlit as st

from src.utils.analysis import (lag_correlations, plot_lag_correlations, plot_sliding_correlation,
                                sliding_correlation)
from src.utils.controls import area_controls, period_slider
from src.utils.nve_api import load_areas, load_data, nve_or_stop
from src.utils.ui import page_header, show_plot
from src.utils.weather_history import WEEKLY_VARIABLES, area_weather_or_stop, weekly_weather_or_stop


# Representative reservoir variables: the weekly change follows the weather more directly than the level.
RESERVOIR_VARIABLES = {
    "fill_level_change": ("Weekly change in fill level", "pp"),
    "fill_level": ("Fill level", "%"),
}
MAX_LAG = 26  # weeks; half a year covers snow that falls in winter and melts in spring


def reservoir_series(frame: pd.DataFrame, area_type: str, number: int, column: str) -> pd.Series:
    """One area's weekly reservoir variable in percent or percentage points, indexed by week."""
    rows = frame.loc[(frame["area_type"] == area_type) & (frame["area_number"] == number)]
    return rows.set_index("date")[column].sort_index() * 100  # fraction -> % (or pp for the change)


def choose_settings() -> tuple[str, str, int, int]:
    """Local controls: weather property, reservoir variable, lag and window length."""
    left, right = st.columns(2)
    weather_column = left.selectbox("Weather property", list(WEEKLY_VARIABLES), index=2,
                                    format_func=lambda name: WEEKLY_VARIABLES[name][0])
    reservoir_column = right.selectbox("Reservoir variable", list(RESERVOIR_VARIABLES),
                                       format_func=lambda name: RESERVOIR_VARIABLES[name][0])
    lag = left.slider("Lag (weeks; positive = weather first)", -MAX_LAG, MAX_LAG, 0)
    window = right.slider("Window length (weeks)", 8, 156, 26, step=2,
                          help="Short windows show how the relation changes; long windows are more stable.")
    return weather_column, reservoir_column, lag, window


def show_statistics(correlations: pd.Series, lag: int, correlation: pd.Series) -> None:
    """Key numbers: correlation at the chosen lag, the strongest lag and the range in the windows."""
    best = correlations.abs().idxmax()
    cards = [("Correlation at this lag", f"{correlations[lag]:.2f}"),
             ("Strongest lag", f"{best} weeks ({correlations[best]:.2f})"),
             ("Window correlation range", f"{correlation.min():.2f} to {correlation.max():.2f}")]
    for column, (label, value) in zip(st.columns(3), cards):
        column.metric(label, value)


def render_page() -> None:
    """Draw the page: shared area and period, local settings, the three-panel plot and the lag bars."""
    page_header("Explore", "Weather vs. reservoir",
                "Sliding window correlation between the weather and the reservoirs of one area.")
    frame = nve_or_stop(load_data)
    areas = nve_or_stop(load_areas)
    weather = weekly_weather_or_stop()
    with st.container(border=True):
        area_type, number, name = area_controls(frame, areas)
        period = period_slider([pd.Timestamp(week) for week in sorted(frame["date"].unique())])
        st.caption("The area and the period are shared with the Map and Forecast pages.")
    weather_column, reservoir_column, lag, window = choose_settings()

    weather_series = area_weather_or_stop(weather, area_type, number, name)[weather_column].loc[period[0]:period[1]]
    reservoir = reservoir_series(frame, area_type, number, reservoir_column).loc[period[0]:period[1]]
    if len(weather_series.dropna()) < window + abs(lag):
        st.warning("The period is too short for this window and lag. Choose a longer period on the Map page "
                   "or above, or a shorter window.")
        st.stop()

    correlation = sliding_correlation(weather_series, reservoir, lag, window)
    correlations = lag_correlations(weather_series, reservoir, MAX_LAG)
    weather_label = f"{WEEKLY_VARIABLES[weather_column][0]} ({WEEKLY_VARIABLES[weather_column][1]})"
    reservoir_label = f"{RESERVOIR_VARIABLES[reservoir_column][0]} ({RESERVOIR_VARIABLES[reservoir_column][1]})"
    show_statistics(correlations, lag, correlation)
    show_plot(plot_sliding_correlation(weather_series, reservoir, correlation, weather_label, reservoir_label,
                                       f"{name}: {window}-week sliding correlation, lag {lag} weeks"))
    show_plot(plot_lag_correlations(correlations, lag))
    st.caption("The correlation is plotted at the last week of each window. Weather comes from MongoDB "
               "(weekly ERA5 means/sums of 6 locations per area); the reservoir data from NVE's API.")


render_page()
