"""Explore – Reservoir data: the Part 1–2 table and plot pages joined into one page with two tabs.

Part 4 joins the old "Data table" and "Data plot" pages, because both show the same NVE data with
the same controls. The download interval (month slider) and the type of area (EL, NO, VASS) are
chosen once at the top (src/utils/controls.py) and used by both tabs:
- Table: one row per area with a fill-level line (LineChartColumn) and one row per API field.
- Plot: one chosen field as interactive Plotly lines, one line per area.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.utils.controls import reservoir_controls
from src.utils.nve_api import (NUMERIC_COLUMNS, PLOT_LABELS, areas_of_type, load_areas, load_data,
                               month_options, national_series, nve_or_stop, select_interval)
from src.utils.ui import ACCENT, NAVY, SERIES_COLOURS, page_header, show_plot


ALL_NUMERIC = "All numeric columns"
CALENDAR_FIELDS = ("iso_year", "iso_week")      # time identifiers, not measurements
CATEGORY_FIELDS = ("area_type", "area_number")  # geographic categories


# ---- Tab 1: tables ----

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


def show_tables(frame: pd.DataFrame, rows: pd.DataFrame, subset: pd.DataFrame,
                areas: pd.DataFrame, area_type: str, first: str) -> None:
    """Table tab: key figures, the area table, the field table and the raw rows."""
    show_key_figures(subset)
    show_area_table(subset, areas, area_type)
    show_field_table(frame, rows, first)
    with st.expander("Show the downloaded rows for this interval and area type"):
        st.dataframe(subset.drop(columns="area"), hide_index=True, width="stretch")


# ---- Tab 2: plots, one function per kind of field ----

def field_lines(subset: pd.DataFrame, column: str) -> go.Figure:
    """One field over time: one line per area, or a single line for ISO year/week.

    ISO year and week are the same for every area on a date, so one line is enough for them.
    """
    few_points = subset["date"].nunique() <= 12  # show markers when there are few weeks
    if column in CALENDAR_FIELDS:
        data = subset.drop_duplicates("date")
        figure = px.line(data, x="date", y=column, markers=few_points, color_discrete_sequence=[NAVY])
        figure.update_yaxes(dtick=1 if data[column].nunique() < 10 else None)  # whole numbers only
    else:
        figure = px.line(subset, x="date", y=column, color="area", markers=few_points,
                         labels={"area": "Area"})
    title, unit = PLOT_LABELS[column]
    return figure.update_layout(title=title, xaxis_title="Week ending", yaxis_title=unit)


def plot_all_numeric(subset: pd.DataFrame) -> go.Figure:
    """Seven small panels that keep each field's own units and vertical scale; one shared legend."""
    order = ["fill_level", "previous_week_fill_level", "stored_energy_twh",
             "capacity_twh", "fill_level_change", "iso_week", "iso_year"]
    figure = make_subplots(rows=4, cols=2, shared_xaxes=True, vertical_spacing=0.07,
                           subplot_titles=[PLOT_LABELS[c][0] for c in order])
    colours = dict(zip(sorted(subset["area"].unique()), SERIES_COLOURS))
    for i, column in enumerate(order):
        row, col = i // 2 + 1, i % 2 + 1
        if column in CALENDAR_FIELDS:
            data = subset.drop_duplicates("date")
            figure.add_trace(go.Scatter(x=data["date"], y=data[column], mode="lines", name=column,
                                        line={"color": NAVY}, showlegend=False), row=row, col=col)
        else:
            for area, group in subset.groupby("area"):
                # legendgroup ties an area's lines in all panels to one legend entry.
                figure.add_trace(go.Scatter(x=group["date"], y=group[column], mode="lines", name=area,
                                            legendgroup=area, showlegend=(i == 0),
                                            line={"color": colours[area], "width": 1.2}),
                                 row=row, col=col)
        figure.update_yaxes(title_text=PLOT_LABELS[column][1], row=row, col=col)
    figure.update_layout(title="All numeric columns — separate scales", height=900,
                         legend={"title": {"text": "Area"}})
    st.info("Each panel has its own vertical scale. ISO year and week identify time; "
            "they are not reservoir measurements.")
    return figure


def plot_dates(subset: pd.DataFrame) -> go.Figure:
    """The date is the x-coordinate itself, so dots show when reports exist."""
    dates = subset["date"].drop_duplicates()
    figure = go.Figure(go.Scatter(x=dates, y=[1] * len(dates), mode="markers",
                                  marker={"color": ACCENT, "size": 8}, hovertemplate="%{x}<extra></extra>"))
    figure.update_yaxes(visible=False, range=[0.8, 1.2])
    return figure.update_layout(title="Reporting dates", xaxis_title="Date", height=300)


def plot_categories(rows: pd.DataFrame, subset: pd.DataFrame, column: str) -> go.Figure:
    """Count records per area type (all types) or per area number (the chosen type)."""
    if column == "area_type":
        categories, note, label = rows["area_type"], "all area types", "Area type"
    else:
        # NVE's names pair the number with its type: EL 1 and VASS 1 are different areas.
        categories, note, label = subset["area"], "the chosen area type", "Area"
    counts = categories.value_counts().sort_index()
    st.info(f"Counts include {note} in the chosen interval.")
    figure = px.bar(x=counts.index, y=counts.values, color_discrete_sequence=[ACCENT])
    return figure.update_layout(title=f"Records by {column}", xaxis_title=label, yaxis_title="API records")


def plot_publication_status(subset: pd.DataFrame) -> go.Figure:
    """Count records of the chosen area type with and without a next publication date."""
    # Year 0001 in the source means that no publication date was supplied; it becomes NaT.
    parsed = pd.to_datetime(subset["next_publication_date"], format="%Y-%m-%dT%H:%M:%S",
                            errors="coerce")
    figure = px.bar(x=["Date supplied", "No date (0001)"], y=[parsed.notna().sum(), parsed.isna().sum()],
                    color_discrete_sequence=[ACCENT])
    return figure.update_layout(title="Next publication date availability", xaxis_title="",
                                yaxis_title="API records")


def choose_field(columns: list[str]) -> str:
    """Select box with every API field plus the combined view; readable labels keep the source name."""
    options = [ALL_NUMERIC, *columns]
    return st.selectbox(
        "API field", options, index=options.index("fill_level"),
        format_func=lambda name: f"{PLOT_LABELS[name][0]} · {name}" if name in PLOT_LABELS else name,
    )


def plot_for_field(field: str, subset: pd.DataFrame, rows: pd.DataFrame) -> go.Figure:
    """Pick the plot that fits the type of field (time series, dates, categories, status)."""
    if field == ALL_NUMERIC:
        return plot_all_numeric(subset)
    if field in NUMERIC_COLUMNS:
        if field in CALENDAR_FIELDS:
            st.info("This is a calendar identifier over time, not a reservoir measurement.")
        return field_lines(subset, field)
    if field == "date":
        return plot_dates(subset)
    if field in CATEGORY_FIELDS:
        return plot_categories(rows, subset, field)
    return plot_publication_status(subset)  # next_publication_date


def show_plots(frame: pd.DataFrame, rows: pd.DataFrame, subset: pd.DataFrame) -> None:
    """Plot tab: field choice, the interactive plot and a short caption."""
    field = choose_field(frame.columns.tolist())
    show_plot(plot_for_field(field, subset, rows))
    st.caption("Hover for values, drag to zoom, double-click to reset. Click an area in the legend to "
               "hide it, double-click to show only that area.")


def render_page() -> None:
    """Draw the page: shared controls, then the Table and Plot tabs."""
    page_header("Explore", "Reservoir data",
                "Get to know NVE's weekly reservoir statistics: one table per area and API field, "
                "and interactive plots of every field.")
    frame = nve_or_stop(load_data)   # full history, cached (src/utils/nve_api.py)
    areas = nve_or_stop(load_areas)  # area names and descriptions (HentOmråder)
    first, last, area_type = reservoir_controls(month_options(frame))
    rows = select_interval(frame, first, last)      # all areas in the interval
    subset = areas_of_type(rows, areas, area_type)  # only the chosen area type
    if subset.empty:
        st.warning("No records in the selected interval.")
        st.stop()

    table_tab, plot_tab = st.tabs(["Table", "Plot"])
    with table_tab:
        show_tables(frame, rows, subset, areas, area_type, first)
    with plot_tab:
        show_plots(frame, rows, subset)
    st.caption(f"{subset['date'].nunique():,} weekly reports · {subset['area'].nunique()} area(s) "
               f"of type {area_type} · {first} to {last}.")


render_page()
