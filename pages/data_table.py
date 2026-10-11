"""One row per field from the NVE API, with a first-month sparkline."""

import pandas as pd
import streamlit as st

from dashboard.nve_api import load_data, national_series
from dashboard.ui import ACCENT, page_header


page_header("IND320 / DATA TABLE", "Get to know the data",
            "One row per API field, with examples and a glimpse of the first month.")
frame = load_data()
series = national_series(frame)
first_month = series["date"].dt.to_period("M").min()
first_month_data = series.loc[series["date"].dt.to_period("M") == first_month]

for col, label, value in zip(st.columns(3),
                             ["API records", "API fields", "First month"],
                             [f"{len(frame):,}", str(len(frame.columns)), str(first_month)]):
    with col, st.container(border=True):
        st.metric(label, value)

# Numeric columns get a line chart. Text/date columns remain visible as rows,
# but do not receive a misleading numeric encoding.
rows = []
numeric_columns = first_month_data.select_dtypes(include="number").columns
for column in frame.columns:
    sparkline = (
        first_month_data[column].dropna().astype(float).tolist()
        if column in numeric_columns
        else []
    )
    rows.append(
        {
            "API field": column,
            "Data type": str(frame[column].dtype),
            "Example": (str(first_month_data[column].dropna().iloc[0])
                        if first_month_data[column].notna().any() else ""),
            "First month": sparkline,
        }
    )

summary = pd.DataFrame(rows)
st.caption(
    f"One row per API field ({len(frame.columns)} total). Sparklines show {first_month} "
    "for the Norway total series (NO, area 0), and examples come from that same series. "
    "Flat lines mean the value stayed "
    "constant; text and date fields have no numeric sparkline."
)
st.dataframe(
    summary,
    hide_index=True,
    width="stretch",
    height=425,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month", width="medium", color=ACCENT
        )
    },
)
with st.expander("Show imported data"):
    st.dataframe(frame, hide_index=True, width="stretch")
st.page_link("pages/about.py", label="What do the area codes and units mean?", icon="ℹ️")
