"""Electricity – Cross-border flows between Norway and its neighbours, read from MongoDB.

Left column: radio buttons choose the connection (neighbour country) and a select box the
year; a donut chart shows the energy that went into and out of Norway that year.
Right column: pills choose which months to include; an interactive Plotly line chart shows the
flows for every link and direction, as in the notebook. Below: an expander documents the data source.
The data were fetched and prepared in the Part 2 notebook (ENTSO-E -> Cassandra/Spark -> MongoDB).
Part 4: the Matplotlib pie and the Altair line chart are replaced by Plotly charts.
"""

import calendar
from collections.abc import Callable
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pymongo.errors import PyMongoError
import streamlit as st

from src.utils.flows_db import (DIRECTION_LABELS, MissingSecrets, load_months, load_options,
                                load_year_totals)
from src.utils.ui import ACCENT, HIGHLIGHT, page_header, show_plot, wide_page


# Fixed colours: imports and exports keep the same colour in every chart on this page.
DIRECTION_COLORS = {"import": ACCENT, "export": HIGHLIGHT}


def read_mongo(loader: Callable[..., Any], *args: Any) -> Any:
    """Run one MongoDB read; on problems show a short message instead of a traceback and stop the page."""
    try:
        return loader(*args)
    except MissingSecrets as error:
        st.error(f"MongoDB is not configured: {error}")
    except PyMongoError as error:  # wrong password, IP not allowed in Atlas, paused cluster, network ...
        st.error(f"Could not read from MongoDB ({type(error).__name__}). Check the connection "
                 "string and that Atlas Network Access allows this app.")
    st.stop()


def load_options_or_stop() -> dict[str, list]:
    """Connections and years from MongoDB; stop the page with a clear message if there are none."""
    options = read_mongo(load_options)
    if not options["neighbours"]:
        st.warning("The MongoDB collection is empty. Run the Part 2 notebook to fill it.")
        st.stop()
    return options


# ---- Left column: yearly balance ----

def yearly_pie_figure(totals: pd.DataFrame, neighbour: str, year: int) -> go.Figure:
    """Donut chart of energy into and out of Norway; hover and legend give every slice's TWh and share."""
    totals = totals.sort_values("direction", ascending=False)  # import first, then export
    twh = totals["energy_mwh"] / 1e6  # 1 TWh = 1,000,000 MWh
    figure = go.Figure(go.Pie(
        labels=[DIRECTION_LABELS[d] for d in totals["direction"]], values=twh, hole=0.45, sort=False,
        marker={"colors": [DIRECTION_COLORS[d] for d in totals["direction"]],
                "line": {"color": "white", "width": 2}},
        texttemplate="%{percent:.0%}<br>%{value:.2f} TWh", textposition="inside",
        hovertemplate="%{label}<br>%{value:.2f} TWh (%{percent:.1%})<extra></extra>"))
    figure.update_layout(title=f"Norway ↔ {neighbour}, {year}", height=420,
                         legend={"orientation": "h", "y": -0.05})
    return figure


def show_yearly_balance(options: dict[str, list]) -> tuple[str, int]:
    """Left column: choose connection and year, show the pie; return the two choices."""
    st.subheader("Yearly balance")
    neighbour = st.radio("Connection", options["neighbours"],
                         format_func=lambda name: f"Norway ↔ {name}")
    year = st.selectbox("Year", options["years"], index=len(options["years"]) - 1)

    totals = read_mongo(load_year_totals, neighbour, year)  # MongoDB sums the hours per direction
    if totals.empty or totals["energy_mwh"].sum() == 0:
        st.info("No flow recorded for this connection and year.")
        return neighbour, year

    show_plot(yearly_pie_figure(totals, neighbour, year))
    by_direction = totals.set_index("direction")["energy_mwh"] / 1e6
    net = by_direction.get("export", 0.0) - by_direction.get("import", 0.0)
    st.caption(f"Net {'export' if net >= 0 else 'import'}: {abs(net):.2f} TWh. "
               "Sum of hourly physical flows over all links on this connection.")
    return neighbour, year


# ---- Right column: flows in the chosen months ----

RESOLUTIONS = ["Hourly", "Daily mean"]
Y_TITLE = "Energy per hour (MWh ≈ average MW)"


def month_segments(months: list[int]) -> dict[int, int]:
    """Give each chosen month a segment number; a new segment starts after a gap (e.g. Jan | Jul).

    The chart draws one line per segment, so it breaks between months that are not next to
    each other instead of drawing a straight line across the missing months.
    """
    segments, segment, previous = {}, 0, None
    for month in sorted(months):
        if previous is not None and month != previous + 1:
            segment += 1
        segments[month], previous = segment, month
    return segments


def month_label(months: list[int]) -> str:
    """Short text for the chosen months: consecutive months as a range, e.g. "Jan–Mar, Jul"."""
    runs: dict[int, list[int]] = {}
    for month, segment in month_segments(months).items():
        runs.setdefault(segment, []).append(month)
    names = [calendar.month_abbr[run[0]] if len(run) == 1
             else f"{calendar.month_abbr[run[0]]}–{calendar.month_abbr[run[-1]]}" for run in runs.values()]
    return ", ".join(names)


def chart_data(data: pd.DataFrame, months: list[int], resolution: str) -> pd.DataFrame:
    """Hourly or daily-mean values per link and direction, ready for the Plotly chart."""
    frame = data
    if resolution == "Daily mean":
        # The mean of the hourly MWh values over a day is still MWh per hour (≈ average MW).
        frame = (data.set_index("time").groupby(["link", "direction"])["energy_mwh"]
                 .resample("D").mean().dropna().reset_index())
    segment = frame["time"].dt.month.map(month_segments(months)).astype(str)
    # One line per link, direction and run of adjacent months, so a gap between months stays empty.
    frame = frame.assign(line=frame["link"] + " " + frame["direction"] + " " + segment)
    # Norwegian wall-clock time without a zone label: Plotly shows naive times exactly as given.
    frame["time"] = frame["time"].dt.tz_localize(None)
    return frame


def months_flows_chart(frame: pd.DataFrame, title: str) -> go.Figure:
    """Interactive line chart: colour = link, solid = import, dashed = export (as in the notebook)."""
    figure = px.line(frame, x="time", y="energy_mwh", color="link", line_dash="direction",
                     line_group="line", line_dash_map={"import": "solid", "export": "dash"},
                     labels={"energy_mwh": Y_TITLE, "link": "Link", "direction": "Direction", "time": ""},
                     hover_data={"line": False, "energy_mwh": ":,.0f"})
    figure.update_traces(line={"width": 1.3})
    figure.update_layout(title=title, height=480, legend={"orientation": "h", "y": -0.15})
    return figure


def show_months_flows(neighbour: str, year: int) -> None:
    """Right column: pills choose the months and a toggle the resolution, then the line chart."""
    st.subheader("Flows by month")
    months = st.pills("Months to include", list(range(1, 13)), selection_mode="multi",
                      default=[1], format_func=lambda m: calendar.month_abbr[m])
    # Daily means give calm, readable lines; "Hourly" shows every hour, as in the notebook.
    resolution = st.segmented_control("Resolution", RESOLUTIONS, default="Daily mean")
    st.caption(f"Connection and year follow the choices on the left: Norway ↔ {neighbour}, {year}. "
               "Hover for values; drag to zoom in time, double-click to reset. Months that are not next "
               "to each other leave a gap in the lines.")
    if not months:
        st.info("Select at least one month.")
        return
    data = read_mongo(load_months, neighbour, year, tuple(sorted(months)))
    if data.empty:
        st.info("No data for these months.")
        return
    resolution = resolution or "Daily mean"  # the toggle returns None if it is clicked off
    title = f"Norway ↔ {neighbour}, {year}: {month_label(months)} ({resolution.lower()})"
    show_plot(months_flows_chart(chart_data(data, months, resolution), title))


# ---- Below the columns ----

def show_data_source() -> None:
    """Expander that documents where the data on this page come from."""
    with st.expander("About the data on this page"):
        st.markdown("""
        - **Source:** [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), data item
          *Cross-Border Physical Flows* (12.1.G, `documentType=A11`), fetched through the RESTful API.
        - **Scope:** the nine links between Norwegian price areas (NO1–NO4) and neighbouring
          price areas in Sweden, Denmark, Finland, Germany, the Netherlands and Great Britain.
          Flows inside Norway are not included.
        - **Directions:** ENTSO-E reports each direction separately (not netted). *Import* means
          into Norway and *export* means out of Norway.
        - **Processing:** the Part 2 notebook stored the raw 15/60-minute values in Cassandra with
          Spark, used Spark to select the relevant columns and sum them to hourly energy (MWh),
          and inserted the result into MongoDB. This page reads only from MongoDB.
        - **Time:** years and months follow Norwegian local time. Energy per hour in MWh equals
          the average power in MW during that hour.
        """)


def render_page() -> None:
    """Draw the page: two columns (yearly pie | line chart by month) and the data-source expander."""
    page_header("Electricity", "Power across the border",
                "Physical electricity flows between Norway and its neighbours, "
                "from ENTSO-E via MongoDB.")
    wide_page()  # two charts side by side need more width than the other pages
    options = load_options_or_stop()
    left, right = st.columns([2, 3], gap="large")  # the line chart gets the larger share
    with left, st.container(border=True):
        neighbour, year = show_yearly_balance(options)
    with right, st.container(border=True):
        show_months_flows(neighbour, year)
    show_data_source()


render_page()
