"""Page 2 – Data table: one row per field from the NVE API, with a first-month sparkline."""

import pandas as pd
import streamlit as st

from src.utils.nve_api import load_data, national_series
from src.utils.ui import ACCENT, page_header


def show_key_figures(frame: pd.DataFrame, first_month: pd.Period) -> None:
    """Three cards: number of records, number of fields and the first month in the data."""
    figures = [("API records", f"{len(frame):,}"),
               ("API fields", str(len(frame.columns))),
               ("First month", str(first_month))]
    for column, (label, value) in zip(st.columns(3), figures):
        with column, st.container(border=True):
            st.metric(label, value)


def field_summary(frame: pd.DataFrame, first_month_data: pd.DataFrame) -> pd.DataFrame:
    """One row per API field: data type, an example value and first-month values.

    Numeric fields get a list of values for the sparkline. Text and date fields get an
    empty list, so they stay visible without a misleading numeric line.
    """
    numeric_columns = first_month_data.select_dtypes(include="number").columns
    rows = []
    for column in frame.columns:
        values = first_month_data[column].dropna()
        rows.append({
            "API field": column,
            "Data type": str(frame[column].dtype),
            "Example": str(values.iloc[0]) if not values.empty else "",
            "First month": values.astype(float).tolist() if column in numeric_columns else [],
        })
    return pd.DataFrame(rows)


def render_page() -> None:
    """Draw the page: key figures, the field summary table and the raw data."""
    page_header("IND320 / DATA TABLE", "Get to know the data",
                "One row per API field, with examples and a glimpse of the first month.")
    frame = load_data()
    series = national_series(frame)  # Norway total (NO, area 0)
    first_month = series["date"].dt.to_period("M").min()
    first_month_data = series.loc[series["date"].dt.to_period("M") == first_month]
    show_key_figures(frame, first_month)

    st.caption(
        f"One row per API field ({len(frame.columns)} total). Sparklines show {first_month} "
        "for the Norway total series (NO, area 0), and examples come from that same series. "
        "Flat lines mean the value stayed constant; text and date fields have no numeric sparkline."
    )
    st.dataframe(
        field_summary(frame, first_month_data),
        hide_index=True,
        width="stretch",
        height=425,
        # The list in "First month" is drawn as a small line chart inside the cell.
        column_config={"First month": st.column_config.LineChartColumn(
            "First month", width="medium", color=ACCENT)},
    )
    with st.expander("Show imported data"):
        st.dataframe(frame, hide_index=True, width="stretch")
    st.page_link("src/pages/about.py", label="What do the area codes and units mean?", icon="ℹ️")


render_page()
