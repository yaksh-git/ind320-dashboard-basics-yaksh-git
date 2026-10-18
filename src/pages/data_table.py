"""Page 2 – Data table: one row per area (with a fill-level line) and one row per API field.

The download interval and the type of area are chosen with the shared controls at the top
(src/utils/controls.py); the same choices are used on the Data plot page.
"""

import pandas as pd
import streamlit as st

from src.utils.controls import reservoir_controls
from src.utils.nve_api import (areas_of_type, load_areas, load_data, month_options,
                               national_series, select_interval)
from src.utils.ui import ACCENT, page_header


def show_key_figures(subset: pd.DataFrame) -> None:
    """Three cards: months in the interval, weekly reports and the number of areas."""
    figures = [("Months in the interval", str(subset["date"].dt.to_period("M").nunique())),
               ("Weekly reports", f"{subset['date'].nunique():,}"),
               ("Areas of this type", str(subset["area"].nunique()))]
    for column, (label, value) in zip(st.columns(3), figures):
        with column, st.container(border=True):
            st.metric(label, value)


def area_table(subset: pd.DataFrame, areas: pd.DataFrame) -> pd.DataFrame:
    """One row per area: the weekly fill level as a list (for the line), latest values and region."""
    descriptions = areas.set_index("name")["description"].to_dict()
    rows = []
    for area, group in subset.sort_values("date").groupby("area"):
        latest = group.iloc[-1]  # the newest week in the interval
        rows.append({
            "Area": area,
            "Fill level over the interval": group["fill_level"].tolist(),
            "Latest fill level": latest["fill_level"],
            "Stored energy (TWh)": latest["stored_energy_twh"],
            "Capacity (TWh)": latest["capacity_twh"],
            "Region (NVE description)": descriptions.get(area, ""),
        })
    return pd.DataFrame(rows)


def show_area_table(subset: pd.DataFrame, areas: pd.DataFrame, area_type: str) -> None:
    """The per-area table; LineChartColumn draws each area's fill level inside its row."""
    st.subheader("One row per area")
    st.caption("Each line shows the weekly fill level (0–100 %) in the chosen interval; "
               "the other columns show the newest week.")
    st.dataframe(
        area_table(subset, areas),
        hide_index=True,
        width="stretch",
        column_config={
            "Fill level over the interval": st.column_config.LineChartColumn(
                "Fill level over the interval", y_min=0.0, y_max=1.0, width="large", color=ACCENT),
            "Latest fill level": st.column_config.ProgressColumn(
                "Latest fill level", format="percent", min_value=0.0, max_value=1.0),
            "Stored energy (TWh)": st.column_config.NumberColumn(format="%.1f"),
            "Capacity (TWh)": st.column_config.NumberColumn(format="%.1f"),
            "Region (NVE description)": st.column_config.TextColumn(width="large"),
        },
    )
    # HentOmråder can list areas that have no data rows (VASS4 in October 2026).
    defined = set(areas.loc[areas["area_type"] == area_type, "name"])
    missing = sorted(defined - set(subset["area"]))
    if missing:
        st.info(f"Listed by the API but without measurements: {', '.join(missing)}.")


def field_summary(frame: pd.DataFrame, month_data: pd.DataFrame) -> pd.DataFrame:
    """One row per API field: data type, an example value and one month of values.

    Numeric fields get a list of values for the sparkline. Text and date fields get an
    empty list, so they stay visible without a misleading numeric line.
    """
    numeric_columns = month_data.select_dtypes(include="number").columns
    rows = []
    for column in frame.columns:
        values = month_data[column].dropna()
        rows.append({
            "API field": column,
            "Data type": str(frame[column].dtype),
            "Example": str(values.iloc[0]) if not values.empty else "",
            "First month": values.astype(float).tolist() if column in numeric_columns else [],
        })
    return pd.DataFrame(rows)


def show_field_table(frame: pd.DataFrame, rows: pd.DataFrame, first: str) -> None:
    """The Part 1 overview: one row per API field, with the interval's first month as a line."""
    st.subheader("One row per API field")
    national = national_series(rows)  # Norway total (NO, area 0), one row per week
    month_data = national.loc[national["date"].dt.to_period("M").astype(str) == first]
    st.caption(f"One row per API field ({len(frame.columns)} total). Lines and examples show {first} "
               "for the Norway total (NO, area 0). Text and date fields have no numeric line.")
    st.dataframe(
        field_summary(frame, month_data),
        hide_index=True,
        width="stretch",
        column_config={"First month": st.column_config.LineChartColumn(
            "First month", width="medium", color=ACCENT)},
    )


def render_page() -> None:
    """Draw the page: shared controls, key figures, the area table, the field table and raw data."""
    page_header("IND320 / DATA TABLE", "Get to know the data",
                "Fill level for every area of one type, and an overview of the API fields.")
    frame = load_data()   # full history, cached (src/utils/nve_api.py)
    areas = load_areas()  # area names and descriptions (HentOmråder)
    first, last, area_type = reservoir_controls(month_options(frame))
    rows = select_interval(frame, first, last)        # all areas in the interval
    subset = areas_of_type(rows, areas, area_type)  # only the chosen area type
    if subset.empty:
        st.warning("No records in the selected interval.")
        st.stop()

    show_key_figures(subset)
    show_area_table(subset, areas, area_type)
    show_field_table(frame, rows, first)
    with st.expander("Show the downloaded rows for this interval and area type"):
        st.dataframe(subset.drop(columns="area"), hide_index=True, width="stretch")
    st.page_link("src/pages/about.py", label="What do the area codes and units mean?", icon="ℹ️")


render_page()
