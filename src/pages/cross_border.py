"""Page 4 – Cross-border flows between Norway and its neighbours, read from MongoDB.

Left column: radio buttons choose the connection (neighbour country) and a select box the
year; a pie chart shows the energy that went into and out of Norway that year.
Right column: pills choose which months to include; a line plot shows the hourly flows for
every link and direction, as in the notebook. Below: an expander documents the data source.
The data were fetched and prepared in the Part 2 notebook (ENTSO-E -> Cassandra/Spark -> MongoDB).
"""

import calendar

from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import pandas as pd
from pymongo.errors import PyMongoError
import seaborn as sns
import streamlit as st

from src.utils.flows_db import (DIRECTION_LABELS, MissingSecrets, load_months, load_options,
                                load_year_totals)
from src.utils.ui import chart_style, page_header, show_figure


# Fixed colours: imports and exports keep the same colour in every chart on this page.
DIRECTION_COLORS = {"import": "#087F8C", "export": "#B35A12"}
FIGURE_SIZE = (6, 4.6)  # same size in both columns, so the two charts line up


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
    figure, axis = plt.subplots(figsize=FIGURE_SIZE)
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


# ---- Right column: hourly flows in the chosen months ----

LINE_STYLES = {"import": "-", "export": "--"}  # solid = into Norway, dashed = out of Norway


def months_flows_figure(data: pd.DataFrame, title: str) -> Figure:
    """Hourly line plot: colour shows the link, line style the direction (as in the notebook)."""
    links = sorted(data["link"].unique())
    colors = dict(zip(links, sns.color_palette(n_colors=len(links))))
    figure, axis = plt.subplots(figsize=FIGURE_SIZE)
    for (link, direction), group in data.groupby(["link", "direction"]):
        # asfreq("h") adds empty hours between months that are not next to each other
        # (e.g. January and July), so the line breaks there instead of jumping across the gap.
        series = group.set_index("time")["energy_mwh"].asfreq("h")
        axis.plot(series.index, series.to_numpy(), color=colors[link],
                  linestyle=LINE_STYLES[direction], linewidth=0.9)
    locator = AutoDateLocator(tz="Europe/Oslo")
    axis.xaxis.set_major_locator(locator)
    axis.xaxis.set_major_formatter(ConciseDateFormatter(locator, tz="Europe/Oslo"))
    axis.set(title=title, xlabel="", ylabel="Energy per hour (MWh ≈ average MW)")
    axis.set_ylim(bottom=0)
    # One legend entry per link (colour) and per direction (line style), below the plot.
    handles = [Line2D([], [], color=colors[link], label=link) for link in links]
    handles += [Line2D([], [], color="#526477", linestyle=style, label=direction)
                for direction, style in LINE_STYLES.items()]
    axis.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3,
                frameon=False, fontsize=8)
    sns.despine(ax=axis)
    return figure


def show_months_flows(neighbour: str, year: int) -> None:
    """Right column: pills choose the months, then the line plot for those months."""
    st.subheader("Hourly flows by month")
    months = st.pills("Months to include", list(range(1, 13)), selection_mode="multi",
                      default=[1], format_func=lambda m: calendar.month_abbr[m])
    st.caption(f"Connection and year follow the choices on the left: Norway ↔ {neighbour}, {year}. "
               "Months that are not next to each other leave a gap in the lines.")
    if not months:
        st.info("Select at least one month.")
        return
    data = load_months(neighbour, year, tuple(sorted(months)))
    if data.empty:
        st.info("No data for these months.")
        return
    names = ", ".join(calendar.month_abbr[m] for m in sorted(months))
    show_figure(months_flows_figure(data, f"Norway ↔ {neighbour}, {year}: {names}"))


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
    """Draw the page: two columns (yearly pie | hourly lines) and the data-source expander."""
    chart_style()
    page_header("IND320 / CROSS-BORDER FLOWS", "Power across the border",
                "Physical electricity flows between Norway and its neighbours, "
                "from ENTSO-E via MongoDB.")
    options = load_options_or_stop()
    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        neighbour, year = show_yearly_balance(options)
    with right, st.container(border=True):
        show_months_flows(neighbour, year)
    show_data_source()


render_page()
