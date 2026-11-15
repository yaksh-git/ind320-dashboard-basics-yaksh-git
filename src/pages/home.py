"""Start – Home: the newest national reservoir report, the long-term fill level and cards to every group.

Data come live from the NVE Magasinstatistikk API (see src/utils/nve_api.py). The cards at the bottom
point to the main page of each menu group (Map, Explore, Anomalies, Forecast, Electricity).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.nve_api import load_data, national_series, nve_or_stop
from src.utils.ui import ACCENT, GROUP_COLOURS, page_header, show_plot


# (group, page file, link text, short description) for the cards at the bottom of the page.
GROUP_CARDS = [
    ("Start", "src/pages/map.py", "Open the map",
     "Colour the areas by fill level or weather and click one to choose it for the other pages."),
    ("Explore", "src/pages/reservoir_data.py", "Reservoir data",
     "Tables and plots of NVE's weekly data, STL and spectrograms, and weather–reservoir correlation."),
    ("Anomalies", "src/pages/weather_outliers.py", "Weather outliers",
     "Outliers (SPC) and anomalies (LOF) in hourly weather for the chosen area."),
    ("Forecast", "src/pages/forecast.py", "Forecast",
     "River models (SNARIMAX or lag regression) with weather and exchange rates as inputs."),
    ("Electricity", "src/pages/cross_border.py", "Cross-border flows",
     "Physical electricity flows between Norway and its neighbours (ENTSO-E via MongoDB)."),
]


def show_latest_metrics(latest: pd.Series) -> None:
    """Three cards with the newest national values (one row of the API data)."""
    cards = [
        ("Reservoir fill level", f"{latest['fill_level']:.1%}", "Share of total capacity"),
        ("Stored energy", f"{latest['stored_energy_twh']:.1f} TWh",
         "Energy equivalent in the reservoirs"),
        ("Reservoir capacity", f"{latest['capacity_twh']:.1f} TWh",
         "Energy equivalent at full capacity"),
    ]
    for column, (label, value, note) in zip(st.columns(3), cards):
        with column, st.container(border=True):
            st.metric(label, value)
            st.caption(note)


def long_view_figure(series: pd.DataFrame) -> go.Figure:
    """Weekly national fill level since 1995 as a thin line with a light fill below."""
    figure = go.Figure(go.Scatter(
        x=series["date"], y=series["fill_level"], mode="lines", fill="tozeroy",
        line={"color": ACCENT, "width": 1}, fillcolor="rgba(8,127,140,0.08)",
        hovertemplate="Week ending %{x|%d %b %Y}<br>%{y:.1%}<extra></extra>"))
    figure.update_layout(height=300, margin={"t": 20}, xaxis_title="Year",
                         yaxis_title="Fill level", yaxis_tickformat=".0%")  # 0.75 -> 75%
    return figure


def show_group_cards() -> None:
    """One card per menu group, coloured like the group, with a link to its main page."""
    columns = st.columns(len(GROUP_CARDS))
    for column, (group, page, label, text) in zip(columns, GROUP_CARDS):
        with column, st.container(border=True):
            st.markdown(f"<span style='color:{GROUP_COLOURS[group]}; font-weight:700; font-size:.78rem; "
                        f"letter-spacing:.12em'>{group.upper()}</span>", unsafe_allow_html=True)
            st.write(text)
            st.page_link(page, label=label)


def render_page() -> None:
    """Draw the page: header, newest values, long-term chart and cards to the menu groups."""
    page_header("Start", "Norway’s water reserves",
                "Explore weekly reservoir levels, the weather behind them, and forecasts of the coming months.")
    frame = nve_or_stop(load_data)   # all areas, cached for six hours
    series = national_series(frame)  # Norway total (NO, area 0)
    latest = series.iloc[-1]         # the newest week returned by the API
    st.caption(f"Live from the NVE API · Latest national report: {latest['date']:%d %B %Y} "
               "· Norway total (NO, area 0)")
    show_latest_metrics(latest)

    st.subheader("The long view")
    st.caption("Weekly fill level for the national series. Hover for values; drag to zoom.")
    show_plot(long_view_figure(series))
    st.subheader("Where to go next")
    show_group_cards()


render_page()
