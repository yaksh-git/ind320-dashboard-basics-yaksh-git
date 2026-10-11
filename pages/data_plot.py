"""Page 3: Seaborn plots with a field selector and an inclusive month range.

Each kind of field gets its own small plotting function below. The bottom of the file
reads the controls, filters the data and calls the function that fits the chosen field.
"""

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import pandas as pd
import seaborn as sns
import streamlit as st

from dashboard.nve_api import NUMERIC_COLUMNS, PLOT_LABELS, load_data, national_series
from dashboard.ui import ACCENT, chart_style, page_header


ALL_NUMERIC = "All numeric columns"
CALENDAR_FIELDS = ("iso_year", "iso_week")      # time identifiers, not measurements
CATEGORY_FIELDS = ("area_type", "area_number")  # geographic categories


def integer_axis(axis, values):
    """Show calendar identifiers as whole numbers, without a misleading wide axis."""
    axis.yaxis.set_major_locator(MaxNLocator(integer=True))
    if values.nunique() == 1:
        # A constant year should not produce a century-wide axis.
        axis.set_ylim(values.iloc[0] - 0.5, values.iloc[0] + 0.5)


def plot_all_numeric(subset):
    """Seven small time-series panels that keep each field's own units and scale."""
    order = ["fill_level", "previous_week_fill_level", "stored_energy_twh",
             "capacity_twh", "fill_level_change", "iso_week", "iso_year"]
    colors = [ACCENT, "#2563A6", "#6D4C91", "#B35A12", "#A63D59", "#637B29", "#334155"]
    figure, axes = plt.subplots(4, 2, figsize=(12, 11), sharex=True)
    for axis, column, color in zip(axes.flat, order, colors):
        sns.lineplot(data=subset, x="date", y=column, estimator=None,
                     errorbar=None, marker="o" if len(subset) <= 12 else None,
                     linewidth=1.5, color=color, ax=axis)
        axis.set(title=PLOT_LABELS[column][0], xlabel="", ylabel=PLOT_LABELS[column][1])
        if column in CALENDAR_FIELDS:
            integer_axis(axis, subset[column])
        sns.despine(ax=axis)
    axes.flat[-1].axis("off")  # 7 panels in a 4 x 2 grid: hide the empty one
    figure.suptitle("All numeric columns — separate scales", fontsize=15)
    figure.autofmt_xdate()
    st.info("Each panel has its own vertical scale. ISO year and week identify time; "
            "they are not reservoir measurements.")
    return figure


def plot_numeric(subset, column):
    """One numeric field as a weekly time series for the Norway total."""
    figure, axis = plt.subplots(figsize=(10, 4.7))
    sns.lineplot(data=subset, x="date", y=column, estimator=None,
                 errorbar=None, marker="o" if len(subset) <= 12 else None,
                 linewidth=2, color=ACCENT, ax=axis)
    axis.set(title=PLOT_LABELS[column][0], xlabel="Date", ylabel=PLOT_LABELS[column][1])
    if column in CALENDAR_FIELDS:
        integer_axis(axis, subset[column])
        st.info("This is a calendar identifier over time, not a reservoir measurement.")
    figure.autofmt_xdate()
    sns.despine(ax=axis)
    return figure


def plot_dates(subset):
    """The date is the x-coordinate itself, so dots show when national reports exist."""
    figure, axis = plt.subplots(figsize=(10, 3.4))
    sns.scatterplot(x=subset["date"], y=[1] * len(subset), s=65, color=ACCENT, ax=axis)
    axis.set(title="Reporting dates", xlabel="Date", ylabel="", yticks=[], ylim=(0.8, 1.2))
    figure.autofmt_xdate()
    sns.despine(ax=axis, left=True)
    return figure


def plot_categories(rows, column):
    """Count records per geographic category over all areas in the date range."""
    categories = rows[column].astype(str)
    if column == "area_number":
        # Pair area numbers with their type: EL 1 and VASS 1 are different areas.
        categories = rows["area_type"] + " " + categories
    counts = categories.value_counts().sort_index().rename_axis("category").reset_index(name="rows")
    figure, axis = plt.subplots(figsize=(9, 4))
    sns.barplot(data=counts, x="category", y="rows", color=ACCENT, errorbar=None, ax=axis)
    axis.set(title=f"Records by {column}",
             xlabel="Area" if column == "area_number" else "Area type", ylabel="API records")
    sns.despine(ax=axis)
    st.info("Category counts include every geographic area in the selected months.")
    return figure


def plot_publication_status(rows):
    """Count records with and without a next publication date."""
    # Year 0001 in the source means that no publication date was supplied; it becomes NaT.
    parsed = pd.to_datetime(rows["next_publication_date"], format="%Y-%m-%dT%H:%M:%S",
                            errors="coerce")
    counts = pd.DataFrame({"status": ["Date supplied", "No date (0001)"],
                           "rows": [parsed.notna().sum(), parsed.isna().sum()]})
    figure, axis = plt.subplots(figsize=(9, 4))
    sns.barplot(data=counts, x="status", y="rows", color=ACCENT, errorbar=None, ax=axis)
    axis.set(title="Next publication date availability", xlabel="", ylabel="API records")
    sns.despine(ax=axis)
    st.info("Status counts include every geographic area in the selected months.")
    return figure


# ---- Page layout and controls ----
chart_style()
page_header("IND320 / INTERACTIVE PLOTS", "Explore the trends",
            "Follow Norway’s reservoir measurements over time, or inspect the source categories.")

frame = load_data()             # all areas, cached API download
series = national_series(frame)  # Norway total (NO, area 0) for time series
months = series["date"].dt.to_period("M").astype(str).unique().tolist()
options = [ALL_NUMERIC, *series.columns.tolist()]
with st.container(border=True):
    # Keep every API field selectable; readable labels retain the source name.
    selected_column = st.selectbox(
        "API field", options, index=options.index("fill_level"),
        format_func=lambda field: (
            f"{PLOT_LABELS[field][0]} · {field}" if field in PLOT_LABELS else field
        ),
    )
    selected_months = st.select_slider(
        "Months (inclusive)", options=months, value=(months[0], months[0]),
    )

# Apply the same month range to all areas (for category counts) and to the national series.
month_values = frame["date"].dt.to_period("M").astype(str)
selected_rows = frame.loc[month_values.between(*selected_months)].copy()
subset = national_series(selected_rows)
if subset.empty:
    st.warning("No records in the selected months.")
    st.stop()

# Choose the plot that fits the type of field.
if selected_column == ALL_NUMERIC:
    figure = plot_all_numeric(subset)
elif selected_column in NUMERIC_COLUMNS:
    figure = plot_numeric(subset, selected_column)
elif selected_column == "date":
    figure = plot_dates(subset)
elif selected_column in CATEGORY_FIELDS:
    figure = plot_categories(selected_rows, selected_column)
else:  # next_publication_date
    figure = plot_publication_status(selected_rows)

figure.tight_layout()
st.pyplot(figure, width="stretch")
plt.close(figure)
period = f"{selected_months[0]} to {selected_months[1]}"
if selected_column in (*CATEGORY_FIELDS, "next_publication_date"):
    st.caption(f"{len(selected_rows):,} API records across all areas · {period}.")
else:
    st.caption(f"{len(subset):,} weekly records · Norway total (NO, area 0) · {period}.")
