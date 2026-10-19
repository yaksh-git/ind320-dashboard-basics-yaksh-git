"""Page 4 – Cross-border flows between Norway and its neighbours, read from MongoDB.

Left column: radio buttons choose the connection (neighbour country) and a select box the
year; a pie chart shows the energy that went into and out of Norway that year.
Right column: pills choose which months to include; an interactive line chart (Altair) shows the
flows for every link and direction, as in the notebook. Below: an expander documents the data source.
The data were fetched and prepared in the Part 2 notebook (ENTSO-E -> Cassandra/Spark -> MongoDB).
"""

import calendar

import altair as alt
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pandas as pd
from pymongo.errors import PyMongoError
import streamlit as st

from src.utils.flows_db import (DIRECTION_LABELS, MissingSecrets, load_months, load_options,
                                load_year_totals)
from src.utils.ui import chart_style, page_header, show_figure, wide_page


# Fixed colours: imports and exports keep the same colour in every chart on this page.
DIRECTION_COLORS = {"import": "#087F8C", "export": "#B35A12"}
PIE_SIZE = (6, 4.6)  # inches; Streamlit scales the figure to the column width


def load_options_or_stop() -> dict[str, list]:
    """Connections and years from MongoDB; stop the page with a clear message on problems."""
    try:
        options = load_options()
    except MissingSecrets as error:
        st.error(f"MongoDB is not configured: {error}")
        st.stop()
    except PyMongoError as error:  # wrong password, IP not allowed in Atlas, network problems, ...
        st.error(f"Could not read from MongoDB ({type(error).__name__}). Check the connection "
                 "string and that Atlas Network Access allows this app.")
        st.stop()
    if not options["neighbours"]:
        st.warning("The MongoDB collection is empty. Run the Part 2 notebook to fill it.")
        st.stop()
    return options


# ---- Left column: yearly balance ----

def yearly_pie_figure(totals: pd.DataFrame, neighbour: str, year: int) -> Figure:
    """Pie chart of energy into and out of Norway; each slice shows its share and TWh."""
    totals = totals.sort_values("direction", ascending=False)  # import first, then export
    twh = totals["energy_mwh"] / 1e6  # 1 TWh = 1,000,000 MWh
    figure, axis = plt.subplots(figsize=PIE_SIZE)
    wedges, _, _ = axis.pie(
        twh,
        colors=[DIRECTION_COLORS[d] for d in totals["direction"]],
        autopct=lambda share: f"{share:.0f}%\n{share * twh.sum() / 100:.2f} TWh",
        pctdistance=0.68,  # place the numbers well inside each slice
        startangle=90, counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"color": "white", "fontweight": "bold"},
    )
    # A legend below the pie instead of labels next to it, so small slices stay readable.
    axis.legend(wedges, [DIRECTION_LABELS[d] for d in totals["direction"]],
                loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2, frameon=False)
    axis.set_title(f"Norway ↔ {neighbour}, {year}")
    return figure


def show_yearly_balance(options: dict[str, list]) -> tuple[str, int]:
    """Left column: choose connection and year, show the pie; return the two choices."""
    st.subheader("Yearly balance")
    neighbour = st.radio("Connection", options["neighbours"],
                         format_func=lambda name: f"Norway ↔ {name}")
    year = st.selectbox("Year", options["years"], index=len(options["years"]) - 1)

    totals = load_year_totals(neighbour, year)  # MongoDB sums the hours per direction
    if totals.empty or totals["energy_mwh"].sum() == 0:
        st.info("No flow recorded for this connection and year.")
        return neighbour, year

    show_figure(yearly_pie_figure(totals, neighbour, year))
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


def chart_data(data: pd.DataFrame, months: list[int], resolution: str) -> pd.DataFrame:
    """Hourly or daily-mean values per link and direction, ready for the Altair chart."""
    frame = data
    if resolution == "Daily mean":
        # The mean of the hourly MWh values over a day is still MWh per hour (≈ average MW).
        frame = (data.set_index("time").groupby(["link", "direction"])["energy_mwh"]
                 .resample("D").mean().dropna().reset_index())
    frame = frame.assign(segment=frame["time"].dt.month.map(month_segments(months)))
    time_format = "%d %b %Y %H:%M" if resolution == "Hourly" else "%d %b %Y"
    frame["when"] = frame["time"].dt.strftime(time_format)  # readable time for the tooltip
    # Norwegian wall-clock time without a zone label, shown as is (see the utc scale below).
    frame["time"] = frame["time"].dt.tz_localize(None)
    return frame


def months_flows_chart(frame: pd.DataFrame, title: str) -> alt.Chart:
    """Interactive line chart: colour = link, solid = import, dashed = export (as in the notebook).

    Hover over a line to see the values; scroll or drag to zoom and move along the time axis.
    """
    return (
        alt.Chart(frame, title=title)
        .mark_line(strokeWidth=1.3)
        .encode(
            # A utc scale shows the times exactly as given, whatever time zone the viewer is in.
            x=alt.X("time:T", scale=alt.Scale(type="utc"), axis=alt.Axis(format="%d %b", title=None)),
            y=alt.Y("energy_mwh:Q", title=Y_TITLE),
            color=alt.Color("link:N", title="Link", legend=alt.Legend(orient="bottom")),
            strokeDash=alt.StrokeDash(  # own legend above the chart, so it is not cut off
                "direction:N", title="Direction", legend=alt.Legend(orient="top", direction="horizontal"),
                scale=alt.Scale(domain=["import", "export"], range=[[1, 0], [6, 3]])),
            detail="segment:N",  # separate line pieces for months that are not adjacent
            tooltip=[alt.Tooltip("when:N", title="Time"), alt.Tooltip("link:N", title="Link"),
                     alt.Tooltip("direction:N", title="Direction"),
                     alt.Tooltip("energy_mwh:Q", title="MWh per hour", format=",.0f")],
        )
        .properties(height=440)
        .interactive(bind_y=False)  # zoom and pan along the time axis only
    )


def show_months_flows(neighbour: str, year: int) -> None:
    """Right column: pills choose the months and a toggle the resolution, then the line chart."""
    st.subheader("Flows by month")
    months = st.pills("Months to include", list(range(1, 13)), selection_mode="multi",
                      default=[1], format_func=lambda m: calendar.month_abbr[m])
    # Daily means give calm, readable lines; "Hourly" shows every hour, as in the notebook.
    resolution = st.segmented_control("Resolution", RESOLUTIONS, default="Daily mean")
    st.caption(f"Connection and year follow the choices on the left: Norway ↔ {neighbour}, {year}. "
               "Hover for values; scroll to zoom in time. Months that are not next to each other "
               "leave a gap in the lines.")
    if not months:
        st.info("Select at least one month.")
        return
    data = load_months(neighbour, year, tuple(sorted(months)))
    if data.empty:
        st.info("No data for these months.")
        return
    names = ", ".join(calendar.month_abbr[m] for m in sorted(months))
    resolution = resolution or "Daily mean"  # the toggle returns None if it is clicked off
    title = f"Norway ↔ {neighbour}, {year}: {names} ({resolution.lower()})"
    chart = months_flows_chart(chart_data(data, months, resolution), title)
    st.altair_chart(chart, width="stretch")


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
    chart_style()
    page_header("IND320 / CROSS-BORDER FLOWS", "Power across the border",
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
