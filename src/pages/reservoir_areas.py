"""Page 4 – Reservoir areas: fill level for every area of one type, live from the NVE API.

Controls: an interval slider chooses the period and radio buttons choose the type of
area (EL, NO or VASS). The line plot has one line per area number.
"""

from datetime import date, timedelta

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter
import pandas as pd
import seaborn as sns
import streamlit as st

from src.utils.nve_api import AREA_TYPES, load_areas, load_data
from src.utils.ui import chart_style, page_header, show_figure


def choose_interval_and_type(first: date, last: date) -> tuple[date, date, str]:
    """Show the interval slider and the area-type radio; return (start, end, area type)."""
    with st.container(border=True):
        # NVE's endpoint has no date parameters: every request returns the full history.
        # The interval slider therefore decides which part of the download is used.
        # Weekly steps from the first Sunday keep both handles on reporting dates.
        start, end = st.slider(
            "Download interval",
            min_value=first,
            max_value=last,
            value=(last - timedelta(weeks=5 * 52), last),  # default: the last five years
            step=timedelta(weeks=1),
            format="YYYY-MM-DD",
        )
        area_type = st.radio("Type of area", list(AREA_TYPES), format_func=AREA_TYPES.get,
                             horizontal=True)
    return start, end, area_type


def select_rows(frame: pd.DataFrame, areas: pd.DataFrame,
                start: date, end: date, area_type: str) -> pd.DataFrame:
    """Rows in the chosen period and area type, with NVE's area name (e.g. "NO 1") added."""
    in_period = frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    subset = frame.loc[in_period & (frame["area_type"] == area_type)].copy()
    names = areas.set_index(["area_type", "area_number"])["name"].to_dict()
    subset["area"] = [names.get((kind, int(number)), f"{kind} {number}")
                      for kind, number in zip(subset["area_type"], subset["area_number"])]
    return subset


def fill_level_figure(subset: pd.DataFrame, area_type: str) -> Figure:
    """One line per area; estimator=None draws the raw weekly values without averaging."""
    figure, axis = plt.subplots(figsize=(11, 4.8))
    sns.lineplot(data=subset, x="date", y="fill_level", hue="area", estimator=None,
                 errorbar=None, linewidth=1.3, ax=axis)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))  # 0.75 -> 75%
    axis.set(title=f"Reservoir fill level — {AREA_TYPES[area_type]}", xlabel="Week ending",
             ylabel="Fill level")
    axis.legend(title="Area", loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    figure.autofmt_xdate()
    sns.despine(ax=axis)
    return figure


def show_latest_table(subset: pd.DataFrame, areas: pd.DataFrame) -> None:
    """The newest week in the period for each area, next to NVE's description of the area."""
    latest = subset.loc[subset["date"] == subset["date"].max()]
    table = latest.merge(areas, on=["area_type", "area_number"], how="left")
    st.subheader(f"Areas in this group · week ending {latest['date'].iloc[0]:%d %b %Y}")
    st.dataframe(
        table[["name", "fill_level", "stored_energy_twh", "capacity_twh", "description"]],
        hide_index=True,
        width="stretch",
        column_config={
            "name": "Area",
            "fill_level": st.column_config.ProgressColumn(
                "Fill level", format="percent", min_value=0.0, max_value=1.0),
            "stored_energy_twh": st.column_config.NumberColumn("Stored (TWh)", format="%.1f"),
            "capacity_twh": st.column_config.NumberColumn("Capacity (TWh)", format="%.1f"),
            "description": st.column_config.TextColumn("Region (NVE description)", width="large"),
        },
    )


def render_page() -> None:
    """Draw the page: controls, the line plot, the latest-week table and a data note."""
    chart_style()
    page_header("IND320 / RESERVOIR AREAS", "Fill level by area",
                "Weekly reservoir data from NVE’s Magasinstatistikk API. "
                "Choose a period and a type of area.")
    frame = load_data()   # full history, downloaded once and cached (src/utils/nve_api.py)
    areas = load_areas()  # area names and descriptions from the HentOmråder endpoint
    start, end, area_type = choose_interval_and_type(frame["date"].min().date(),
                                                     frame["date"].max().date())
    subset = select_rows(frame, areas, start, end, area_type)
    if subset.empty:
        st.warning("No records in the selected interval.")
        st.stop()

    show_figure(fill_level_figure(subset, area_type))
    st.caption(f"{subset['date'].nunique():,} weekly reports · {start:%d %b %Y} to {end:%d %b %Y}.")
    show_latest_table(subset, areas)

    # HentOmråder can list areas that have no data rows (VASS4 in October 2026).
    defined = set(areas.loc[areas["area_type"] == area_type, "name"])
    missing = sorted(defined - set(subset["area"]))
    if missing:
        st.info(f"Listed by the API but without measurements in this period: {', '.join(missing)}.")


render_page()
