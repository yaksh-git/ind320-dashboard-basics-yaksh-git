"""Page 1 – Home: the newest national reservoir report and the long-term fill level.

Data come live from the NVE Magasinstatistikk API (see src/utils/nve_api.py).
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter
import pandas as pd
import streamlit as st

from src.utils.nve_api import load_data, national_series, nve_or_stop
from src.utils.ui import ACCENT, chart_style, page_header, show_figure


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


def long_view_figure(series: pd.DataFrame) -> Figure:
    """Weekly national fill level since 1995 as a thin line with a light fill below."""
    figure, axis = plt.subplots(figsize=(11, 2.8))
    axis.plot(series["date"], series["fill_level"], color=ACCENT, linewidth=0.9)
    axis.fill_between(series["date"], series["fill_level"], color=ACCENT, alpha=0.08)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))  # 0.75 -> 75%
    axis.set(xlabel="Year", ylabel="Fill level")
    return figure


def show_navigation_cards(frame: pd.DataFrame) -> None:
    """Two cards that lead to the table page and the plot page."""
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("Understand the fields")
        st.write(f"{len(frame):,} API records, {len(frame.columns)} fields "
                 "and nine geographic series.")
        st.page_link("src/pages/data_table.py", label="Explore the data table", icon="📋")
    with right, st.container(border=True):
        st.subheader("Find a pattern")
        st.write("Choose a measurement and a month range to explore the weekly records.")
        st.page_link("src/pages/data_plot.py", label="Open the interactive plots", icon="📈")


def render_page() -> None:
    """Draw the page: header, newest values, long-term chart and links to other pages."""
    page_header("IND320 / NORWEGIAN RESERVOIRS", "Norway’s water reserves",
                "Explore weekly reservoir levels, understand the data, and compare trends over time.")
    frame = nve_or_stop(load_data)   # all areas, cached for six hours
    series = national_series(frame)  # Norway total (NO, area 0)
    latest = series.iloc[-1]         # the newest week returned by the API
    st.caption(f"Live from the NVE API · Latest national report: {latest['date']:%d %B %Y} "
               "· Norway total (NO, area 0)")
    show_latest_metrics(latest)

    st.subheader("The long view")
    st.caption("Weekly fill level for the national series. "
               "The detailed plot page lets you choose a shorter period.")
    chart_style()
    show_figure(long_view_figure(series))
    show_navigation_cards(frame)


render_page()
