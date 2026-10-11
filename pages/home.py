"""Overview of the live NVE data, with national metrics and a historical chart."""

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import streamlit as st

from dashboard.nve_api import load_data, national_series
from dashboard.ui import ACCENT, chart_style, page_header


page_header("IND320 / NORWEGIAN RESERVOIRS", "Norway’s water reserves",
            "Explore weekly reservoir levels, understand the data, and compare trends over time.")
frame = load_data()
series = national_series(frame)
latest = series.iloc[-1]
st.caption(f"Live from the NVE API · Latest national report: {latest['date']:%d %B %Y} · Norway total (NO, area 0)")

# These values come from the newest week returned by the API (cached for six hours).
for column, label, value, note in zip(
    st.columns(3),
    ["Reservoir fill level", "Stored energy", "Reservoir capacity"],
    [f"{latest['fill_level']:.1%}", f"{latest['stored_energy_twh']:.1f} TWh",
     f"{latest['capacity_twh']:.1f} TWh"],
    ["Share of total capacity", "Energy equivalent in the reservoirs", "Energy equivalent at full capacity"],
):
    with column, st.container(border=True):
        st.metric(label, value)
        st.caption(note)

st.subheader("The long view")
st.caption("Weekly fill level for the national series. The detailed plot page lets you choose a shorter period.")
chart_style()
figure, axis = plt.subplots(figsize=(11, 2.8))
axis.plot(series["date"], series["fill_level"], color=ACCENT, linewidth=0.9)
axis.fill_between(series["date"], series["fill_level"], color=ACCENT, alpha=0.08)
axis.yaxis.set_major_formatter(PercentFormatter(1.0))
axis.set(xlabel="Year", ylabel="Fill level")
figure.tight_layout()
st.pyplot(figure, width="stretch")
plt.close(figure)

left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("Understand the fields")
    st.write(f"{len(frame):,} API records, {len(frame.columns)} fields and nine geographic series.")
    st.page_link("pages/data_table.py", label="Explore the data table", icon="📋")
with right, st.container(border=True):
    st.subheader("Find a pattern")
    st.write("Choose a measurement and a month range to explore the weekly records.")
    st.page_link("pages/data_plot.py", label="Open the interactive plots", icon="📈")
