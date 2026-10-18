"""Page 6 – Cross-border flows between Norway and its neighbours, read from MongoDB.

Left column: radio buttons choose the connection (neighbour country) and a select box the
year; a pie chart shows the energy that went into and out of Norway that year.
Right column: pills choose the links and directions and a select box the month; a line
plot shows the hourly flows. Below: an expander documents the data source.
The data were fetched and prepared in the Part 2 notebook (ENTSO-E -> Cassandra/Spark -> MongoDB).
"""

import calendar

from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd
from pymongo.errors import PyMongoError
import seaborn as sns
import streamlit as st

from src.utils.flows_db import (DIRECTION_LABELS, MissingSecrets, load_flows_for, load_month,
                                load_options, load_year_totals)
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


# ---- Right column: hourly flows in one month ----

def monthly_flows_figure(shown: pd.DataFrame, month: int, year: int) -> Figure:
    """Hourly line plot: colour shows the link, solid line = import and dashed line = export."""
    figure, axis = plt.subplots(figsize=FIGURE_SIZE)
    sns.lineplot(data=shown, x="time", y="energy_mwh", hue="link", style="direction",
                 style_order=["import", "export"], estimator=None, errorbar=None,
                 linewidth=1, ax=axis)
    axis.set(title=f"{calendar.month_name[month]} {year}", xlabel="Day of month",
             ylabel="Energy per hour (MWh ≈ average MW)")
    axis.xaxis.set_major_formatter(DateFormatter("%d", tz="Europe/Oslo"))  # 01, 02, ... 31
    axis.set_ylim(bottom=0)
    # Legend below the plot, so the plot keeps the full column width. Seaborn adds the
    # group titles "link" and "direction" as extra entries; leave them out.
    handles, labels = axis.get_legend_handles_labels()
    entries = [(h, l) for h, l in zip(handles, labels) if l not in ("link", "direction")]
    axis.legend(*zip(*entries), loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3,
                frameon=False, fontsize=8)
    sns.despine(ax=axis)
    return figure


def show_monthly_flows(neighbour: str, year: int) -> None:
    """Right column: pills for links/directions and a month box, then the line plot."""
    st.subheader("Hourly flows in one month")
    flows = load_flows_for(neighbour)["flow"].tolist()  # e.g. "NO1 → SE3", "SE3 → NO1"
    # The key includes the connection, so the selection resets when the connection changes.
    selected = st.pills("Links and directions", flows, selection_mode="multi",
                        default=flows, key=f"pills_{neighbour}")
    month = st.selectbox("Month", range(1, 13), format_func=lambda m: calendar.month_name[m])
    st.caption(f"Connection and year follow the choices on the left: Norway ↔ {neighbour}, {year}.")

    month_data = load_month(neighbour, year, month)
    if not selected:
        st.info("Select at least one link and direction.")
    elif month_data.empty:
        st.info("No data for this month.")
    else:
        # Combine connection + year (left), month and the selected links/directions (right).
        shown = month_data.loc[month_data["flow"].isin(selected)]
        show_figure(monthly_flows_figure(shown, month, year))


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
    """Draw the page: two columns (yearly pie | monthly lines) and the data-source expander."""
    chart_style()
    page_header("IND320 / CROSS-BORDER FLOWS", "Power across the border",
                "Physical electricity flows between Norway and its neighbours, "
                "from ENTSO-E via MongoDB.")
    options = load_options_or_stop()
    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        neighbour, year = show_yearly_balance(options)
    with right, st.container(border=True):
        show_monthly_flows(neighbour, year)
    show_data_source()


render_page()
