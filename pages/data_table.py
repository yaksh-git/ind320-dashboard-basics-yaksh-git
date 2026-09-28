"""One row per imported CSV column, with a first-month sparkline."""

import pandas as pd
import streamlit as st

from data_utils import load_data, national_series


st.title("Data table")
st.caption("A readable summary of all 11 CSV fields. Open the section below for every source row.")
frame = load_data()
series = national_series(frame)
first_month = series["date"].dt.to_period("M").min()
first_month_data = series.loc[series["date"].dt.to_period("M") == first_month]

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
            "CSV column": column,
            "Data type": str(frame[column].dtype),
            "Example": (str(first_month_data[column].dropna().iloc[0])
                        if first_month_data[column].notna().any() else ""),
            "First month": sparkline,
        }
    )

summary = pd.DataFrame(rows)
st.caption(
    f"One row per CSV column ({len(frame.columns)} total). Sparklines show {first_month} "
    "for the Norway total series (NO, area 0), and examples come from that same series. "
    "Flat lines mean the value stayed "
    "constant; text and date fields have no numeric sparkline."
)
st.dataframe(
    summary,
    hide_index=True,
    width="stretch",
    height=510,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month", width="medium", color="#2563A6"
        )
    },
)
with st.expander("Show imported data"):
    st.dataframe(frame, hide_index=True, width="stretch")
