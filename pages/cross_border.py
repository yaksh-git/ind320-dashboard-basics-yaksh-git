"""Page 6: cross-border electricity flows between Norway and its neighbours (MongoDB).

Left column: radio buttons choose the connection (neighbour country) and a select box
the year; a pie chart shows the energy that went into and out of Norway that year.
Right column: pills choose the links and directions, a select box the month; a line
plot shows the hourly flows. The data were prepared in the Part 2 notebook.
"""

import calendar

import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

from pymongo.errors import PyMongoError

from dashboard.flows_db import (DIRECTION_LABELS, MissingSecrets, load_flows_for, load_month,
                                load_options, load_year_totals)
from dashboard.ui import chart_style, page_header


# Fixed colours: imports and exports keep the same colour in every chart on this page.
DIRECTION_COLORS = {"import": "#087F8C", "export": "#B35A12"}

chart_style()
page_header("IND320 / CROSS-BORDER FLOWS", "Power across the border",
            "Physical electricity flows between Norway and its neighbours, from ENTSO-E via MongoDB.")

try:
    options = load_options()
except MissingSecrets as error:
    st.error(f"MongoDB is not configured: {error}")
    st.stop()
except PyMongoError as error:  # wrong password, IP not allowed in Atlas, network problems, ...
    st.error(f"Could not read from MongoDB ({type(error).__name__}). Check the connection string "
             "and that Atlas Network Access allows this app.")
    st.stop()
if not options["neighbours"]:
    st.warning("The MongoDB collection is empty. Run the Part 2 notebook to fill it.")
    st.stop()

left, right = st.columns(2, gap="large")

with left, st.container(border=True):
    st.subheader("Yearly balance")
    neighbour = st.radio("Connection", options["neighbours"],
                         format_func=lambda name: f"Norway ↔ {name}", horizontal=True)
    year = st.selectbox("Year", options["years"], index=len(options["years"]) - 1)

    # MongoDB aggregates the hourly documents to one total per direction.
    totals = load_year_totals(neighbour, year)
    if totals.empty or totals["energy_mwh"].sum() == 0:
        st.info("No flow recorded for this connection and year.")
    else:
        totals = totals.sort_values("direction", ascending=False)  # import, then export
        twh = totals["energy_mwh"] / 1e6  # 1 TWh = 1,000,000 MWh
        figure, axis = plt.subplots(figsize=(5, 4.4))
        axis.pie(
            twh,
            labels=[DIRECTION_LABELS[d] for d in totals["direction"]],
            colors=[DIRECTION_COLORS[d] for d in totals["direction"]],
            # Show both the share and the amount on each slice.
            autopct=lambda share: f"{share:.0f}%\n{share * twh.sum() / 100:.2f} TWh",
            startangle=90, counterclock=False,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
            textprops={"color": "#12263A"},
        )
        axis.set_title(f"Norway ↔ {neighbour}, {year}")
        figure.tight_layout()
        st.pyplot(figure, width="stretch")
        plt.close(figure)
        net = (twh[totals["direction"] == "export"].sum()
               - twh[totals["direction"] == "import"].sum())
        st.caption(f"Net {'export' if net >= 0 else 'import'}: {abs(net):.2f} TWh. "
                   "Sum of hourly physical flows over all links on this connection.")

with right, st.container(border=True):
    st.subheader("Hourly flows in one month")
    # Every link and direction on the chosen connection becomes one pill.
    flows = load_flows_for(neighbour)
    selected = st.pills("Links and directions", flows["flow"].tolist(), selection_mode="multi",
                        default=flows["flow"].tolist(), key=f"pills_{neighbour}")
    month = st.selectbox("Month", range(1, 13), format_func=lambda m: calendar.month_name[m])
    st.caption(f"Connection and year follow the choices on the left: Norway ↔ {neighbour}, {year}.")

    month_data = load_month(neighbour, year, month)
    if not selected:
        st.info("Select at least one link and direction.")
    elif month_data.empty:
        st.info("No data for this month.")
    else:
        # Combine connection, year, month and the selected links/directions.
        shown = month_data.loc[month_data["flow"].isin(selected)]
        figure, axis = plt.subplots(figsize=(6, 4.4))
        # Colour separates the links; solid lines are imports, dashed lines exports.
        sns.lineplot(data=shown, x="time", y="energy_mwh", hue="flow", style="direction",
                     style_order=["import", "export"], estimator=None, errorbar=None,
                     linewidth=1, ax=axis)
        axis.set(title=f"{calendar.month_name[month]} {year}", xlabel="",
                 ylabel="Energy per hour (MWh ≈ average MW)")
        axis.set_ylim(bottom=0)
        axis.legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
        figure.autofmt_xdate()
        sns.despine(ax=axis)
        figure.tight_layout()
        st.pyplot(figure, width="stretch")
        plt.close(figure)

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
