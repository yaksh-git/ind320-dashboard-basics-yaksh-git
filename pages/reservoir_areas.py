"""Page 4: fill level for every area of one type, read live from the NVE API.

Controls: an interval slider chooses the period and radio buttons choose the type
of area (EL, NO or VASS). One line is drawn per area number.
"""

from datetime import timedelta

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd
import seaborn as sns
import streamlit as st

from dashboard.nve_api import AREA_TYPES, load_areas, load_data
from dashboard.ui import chart_style, page_header


chart_style()
page_header("IND320 / RESERVOIR AREAS", "Fill level by area",
            "Weekly reservoir data from NVE’s Magasinstatistikk API. Choose a period and a type of area.")

frame = load_data()   # Full history, downloaded once and cached (see dashboard/nve_api.py).
areas = load_areas()  # Area names and descriptions from the HentOmråder endpoint.
first_date, last_date = frame["date"].min().date(), frame["date"].max().date()

with st.container(border=True):
    # NVE's endpoint has no date parameters: every request returns the full history.
    # The interval slider therefore decides which part of the download is used.
    # Weekly steps from the first Sunday keep both handles on reporting dates.
    start, end = st.slider(
        "Download interval",
        min_value=first_date,
        max_value=last_date,
        value=(last_date - timedelta(weeks=5 * 52), last_date),
        step=timedelta(weeks=1),
        format="YYYY-MM-DD",
    )
    area_type = st.radio("Type of area", list(AREA_TYPES), format_func=AREA_TYPES.get,
                         horizontal=True)

# Keep only the chosen period and area type.
in_period = frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))
subset = frame.loc[in_period & (frame["area_type"] == area_type)].copy()
if subset.empty:
    st.warning("No records in the selected interval.")
    st.stop()

# Label each line with NVE's own area name, e.g. "NO 1" or "VASS1".
names = areas.set_index(["area_type", "area_number"])["name"].to_dict()
subset["area"] = [names.get((kind, int(number)), f"{kind} {number}")
                  for kind, number in zip(subset["area_type"], subset["area_number"])]

# One line per area number. estimator=None draws the raw weekly values, no averaging.
figure, axis = plt.subplots(figsize=(11, 4.8))
sns.lineplot(data=subset, x="date", y="fill_level", hue="area", estimator=None,
             errorbar=None, linewidth=1.3, ax=axis)
axis.yaxis.set_major_formatter(PercentFormatter(1.0))
axis.set(title=f"Reservoir fill level — {AREA_TYPES[area_type]}", xlabel="Week ending",
         ylabel="Fill level")
axis.legend(title="Area", loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
figure.autofmt_xdate()
sns.despine(ax=axis)
figure.tight_layout()
st.pyplot(figure, width="stretch")
plt.close(figure)
st.caption(f"{subset['date'].nunique():,} weekly reports · {start:%d %b %Y} to {end:%d %b %Y}.")

# The newest week in the period, together with NVE's description of each area.
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

# HentOmråder can list areas that have no data rows (VASS4 in October 2026).
defined = set(areas.loc[areas["area_type"] == area_type, "name"])
missing = sorted(defined - set(subset["area"]))
if missing:
    st.info(f"Listed by the API but without measurements in this period: {', '.join(missing)}.")
