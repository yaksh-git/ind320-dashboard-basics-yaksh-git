"""Page 3 – Data plot: Seaborn plots of one chosen field, one line per area number.

The download interval (month slider) and the type of area (EL, NO, VASS) come from the shared
controls at the top (src/utils/controls.py), the same as on the Data table page. Each kind of
field has its own small plotting function; render_page() at the bottom ties them together.
"""

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import pandas as pd
import seaborn as sns
import streamlit as st

from src.utils.controls import reservoir_controls
from src.utils.nve_api import (NUMERIC_COLUMNS, PLOT_LABELS, areas_of_type, load_areas,
                               load_data, month_options, nve_or_stop, select_interval)
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


def draw_field(axis: Axes, subset: pd.DataFrame, column: str, legend: bool) -> None:
    """One field over time: one line per area, or a single line for ISO year/week.

    ISO year and week are the same for every area on a date, so one line is enough.
    estimator=None draws the raw weekly values without averaging.
    """
    few_points = subset["date"].nunique() <= 12  # show markers when there are few weeks
    if column in CALENDAR_FIELDS:
        sns.lineplot(data=subset.drop_duplicates("date"), x="date", y=column, estimator=None,
                     errorbar=None, marker="o" if few_points else None, color="#334155", ax=axis)
        integer_axis(axis, subset[column])
    else:
        sns.lineplot(data=subset, x="date", y=column, hue="area", estimator=None, errorbar=None,
                     marker="o" if few_points else None, linewidth=1.3, legend=legend, ax=axis)
    sns.despine(ax=axis)


def plot_all_numeric(subset: pd.DataFrame) -> Figure:
    """Seven small panels that keep each field's own units; the legend fills the eighth panel."""
    order = ["fill_level", "previous_week_fill_level", "stored_energy_twh",
             "capacity_twh", "fill_level_change", "iso_week", "iso_year"]
    figure, axes = plt.subplots(4, 2, figsize=(12, 11), sharex=True)
    for axis, column in zip(axes.flat, order):
        draw_field(axis, subset, column, legend=(column == order[0]))
        axis.set(title=PLOT_LABELS[column][0], xlabel="", ylabel=PLOT_LABELS[column][1])
    # Move the area legend from the first panel to the empty last panel.
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[0].get_legend().remove()
    axes.flat[-1].axis("off")
    axes.flat[-1].legend(handles, labels, title="Area", loc="center", frameon=False)
    figure.suptitle("All numeric columns — separate scales", fontsize=15)
    figure.autofmt_xdate()
    st.info("Each panel has its own vertical scale. ISO year and week identify time; "
            "they are not reservoir measurements.")
    return figure


def plot_numeric(subset: pd.DataFrame, column: str) -> Figure:
    """One numeric field as weekly time series, one line per area."""
    figure, axis = plt.subplots(figsize=(10, 4.7))
    draw_field(axis, subset, column, legend=True)
    axis.set(title=PLOT_LABELS[column][0], xlabel="Week ending", ylabel=PLOT_LABELS[column][1])
    if column in CALENDAR_FIELDS:
        st.info("This is a calendar identifier over time, not a reservoir measurement.")
    else:
        axis.legend(title="Area", loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    figure.autofmt_xdate()
    return figure


def plot_dates(subset: pd.DataFrame) -> Figure:
    """The date is the x-coordinate itself, so dots show when reports exist."""
    dates = subset["date"].drop_duplicates()
    figure, axis = plt.subplots(figsize=(10, 3.4))
    sns.scatterplot(x=dates, y=[1] * len(dates), s=65, color=ACCENT, ax=axis)
    axis.set(title="Reporting dates", xlabel="Date", ylabel="", yticks=[], ylim=(0.8, 1.2))
    figure.autofmt_xdate()
    sns.despine(ax=axis, left=True)
    return figure


def plot_categories(rows: pd.DataFrame, subset: pd.DataFrame, column: str) -> Figure:
    """Count records per area type (all types) or per area number (the chosen type)."""
    if column == "area_type":
        categories, note = rows["area_type"], "all area types"
    else:
        # NVE's names pair the number with its type: EL 1 and VASS 1 are different areas.
        categories, note = subset["area"], "the chosen area type"
    counts = categories.value_counts().sort_index().rename_axis("category").reset_index(name="rows")
    figure, axis = plt.subplots(figsize=(9, 4))
    sns.barplot(data=counts, x="category", y="rows", color=ACCENT, errorbar=None, ax=axis)
    axis.set(title=f"Records by {column}",
             xlabel="Area" if column == "area_number" else "Area type", ylabel="API records")
    sns.despine(ax=axis)
    st.info(f"Counts include {note} in the chosen interval.")
    return figure


def plot_publication_status(subset: pd.DataFrame) -> Figure:
    """Count records of the chosen area type with and without a next publication date."""
    # Year 0001 in the source means that no publication date was supplied; it becomes NaT.
    parsed = pd.to_datetime(subset["next_publication_date"], format="%Y-%m-%dT%H:%M:%S",
                            errors="coerce")
    counts = pd.DataFrame({"status": ["Date supplied", "No date (0001)"],
                           "rows": [parsed.notna().sum(), parsed.isna().sum()]})
    figure, axis = plt.subplots(figsize=(9, 4))
    sns.barplot(data=counts, x="status", y="rows", color=ACCENT, errorbar=None, ax=axis)
    axis.set(title="Next publication date availability", xlabel="", ylabel="API records")
    sns.despine(ax=axis)
    return figure


# ---- Page flow ----

def choose_field(columns: list[str]) -> str:
    """Select box with every API field plus the combined view; readable labels keep the source name."""
    options = [ALL_NUMERIC, *columns]
    return st.selectbox(
        "API field", options, index=options.index("fill_level"),
        format_func=lambda name: f"{PLOT_LABELS[name][0]} · {name}" if name in PLOT_LABELS else name,
    )


def plot_for_field(field: str, subset: pd.DataFrame, rows: pd.DataFrame) -> Figure:
    """Pick the plot that fits the type of field (time series, dates, categories, status)."""
    if field == ALL_NUMERIC:
        return plot_all_numeric(subset)
    if field in NUMERIC_COLUMNS:
        return plot_numeric(subset, field)
    if field == "date":
        return plot_dates(subset)
    if field in CATEGORY_FIELDS:
        return plot_categories(rows, subset, field)
    return plot_publication_status(subset)  # next_publication_date


def render_page() -> None:
    """Draw the page: shared controls, field choice, the plot and a short caption."""
    chart_style()
    page_header("IND320 / INTERACTIVE PLOTS", "Explore the trends",
                "Follow the reservoir measurements over time, one line per area.")
    frame = nve_or_stop(load_data)   # full history, cached (src/utils/nve_api.py)
    areas = nve_or_stop(load_areas)  # area names (HentOmråder)
    first, last, area_type = reservoir_controls(month_options(frame))
    field = choose_field(frame.columns.tolist())

    rows = select_interval(frame, first, last)        # all areas in the interval
    subset = areas_of_type(rows, areas, area_type)  # only the chosen area type
    if subset.empty:
        st.warning("No records in the selected interval.")
        st.stop()

    show_figure(plot_for_field(field, subset, rows))
    st.caption(f"{subset['date'].nunique():,} weekly reports · {subset['area'].nunique()} area(s) "
               f"of type {area_type} · {first} to {last}.")


render_page()
