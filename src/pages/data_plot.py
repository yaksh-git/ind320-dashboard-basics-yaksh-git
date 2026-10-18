"""Page 3 – Data plot: Seaborn plots of one chosen field over an inclusive month range.

Each kind of field has its own small plotting function. render_page() at the bottom reads
the controls, filters the data and calls the function that fits the chosen field.
"""

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import pandas as pd
import seaborn as sns
import streamlit as st

from src.utils.nve_api import NUMERIC_COLUMNS, PLOT_LABELS, load_data, national_series
from src.utils.ui import ACCENT, chart_style, page_header, show_figure


ALL_NUMERIC = "All numeric columns"
CALENDAR_FIELDS = ("iso_year", "iso_week")      # time identifiers, not measurements
CATEGORY_FIELDS = ("area_type", "area_number")  # geographic categories


# ---- Plot functions: one per kind of field ----

def integer_axis(axis: Axes, values: pd.Series) -> None:
    """Show calendar identifiers as whole numbers, without a misleading wide axis."""
    axis.yaxis.set_major_locator(MaxNLocator(integer=True))
    if values.nunique() == 1:
        # A constant year should not produce a century-wide axis.
        axis.set_ylim(values.iloc[0] - 0.5, values.iloc[0] + 0.5)


def plot_all_numeric(subset: pd.DataFrame) -> Figure:
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


def plot_numeric(subset: pd.DataFrame, column: str) -> Figure:
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


def plot_dates(subset: pd.DataFrame) -> Figure:
    """The date is the x-coordinate itself, so dots show when national reports exist."""
    figure, axis = plt.subplots(figsize=(10, 3.4))
    sns.scatterplot(x=subset["date"], y=[1] * len(subset), s=65, color=ACCENT, ax=axis)
    axis.set(title="Reporting dates", xlabel="Date", ylabel="", yticks=[], ylim=(0.8, 1.2))
    figure.autofmt_xdate()
    sns.despine(ax=axis, left=True)
    return figure


def plot_categories(rows: pd.DataFrame, column: str) -> Figure:
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


def plot_publication_status(rows: pd.DataFrame) -> Figure:
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


# ---- Page flow ----

def choose_field_and_months(series: pd.DataFrame) -> tuple[str, tuple[str, str]]:
    """Show the two controls and return the chosen field and (first, last) month."""
    months = series["date"].dt.to_period("M").astype(str).unique().tolist()
    options = [ALL_NUMERIC, *series.columns.tolist()]
    with st.container(border=True):
        # Every API field is selectable; readable labels keep the source name visible.
        field = st.selectbox(
            "API field", options, index=options.index("fill_level"),
            format_func=lambda name: (
                f"{PLOT_LABELS[name][0]} · {name}" if name in PLOT_LABELS else name),
        )
        month_range = st.select_slider("Months (inclusive)", options=months,
                                       value=(months[0], months[0]))
    return field, month_range


def plot_for_field(field: str, subset: pd.DataFrame, rows: pd.DataFrame) -> Figure:
    """Pick the plot that fits the type of field (time series, dates, categories, status)."""
    if field == ALL_NUMERIC:
        return plot_all_numeric(subset)
    if field in NUMERIC_COLUMNS:
        return plot_numeric(subset, field)
    if field == "date":
        return plot_dates(subset)
    if field in CATEGORY_FIELDS:
        return plot_categories(rows, field)
    return plot_publication_status(rows)  # next_publication_date


def render_page() -> None:
    """Draw the page: controls, the plot for the chosen field and a short caption."""
    chart_style()
    page_header("IND320 / INTERACTIVE PLOTS", "Explore the trends",
                "Follow Norway’s reservoir measurements over time, or inspect the source categories.")
    frame = load_data()              # all areas, cached API download
    series = national_series(frame)  # Norway total (NO, area 0) for time series
    field, (first, last) = choose_field_and_months(series)

    # Apply the same month range to all areas (category counts) and to the national series.
    month_values = frame["date"].dt.to_period("M").astype(str)
    rows = frame.loc[month_values.between(first, last)].copy()
    subset = national_series(rows)
    if subset.empty:
        st.warning("No records in the selected months.")
        st.stop()

    show_figure(plot_for_field(field, subset, rows))
    if field in (*CATEGORY_FIELDS, "next_publication_date"):
        st.caption(f"{len(rows):,} API records across all areas · {first} to {last}.")
    else:
        st.caption(f"{len(subset):,} weekly records · Norway total (NO, area 0) · {first} to {last}.")


render_page()
