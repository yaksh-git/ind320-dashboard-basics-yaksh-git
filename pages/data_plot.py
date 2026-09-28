"""Seaborn plots with a column selector and an inclusive month range."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from data_utils import NUMERIC_COLUMNS, PLOT_LABELS, load_data, national_series


sns.set_theme(style="whitegrid", palette="deep")
st.title("Reservoir data plot")
st.caption("Weekly data for Norway total (NO, area 0). Choose a field and a month range.")

frame = load_data()
series = national_series(frame)
months = series["date"].dt.to_period("M").astype(str).unique().tolist()
options = ["All numeric columns", *series.columns.tolist()]
selected_column = st.selectbox("CSV column", options, index=options.index("fill_level"))
selected_months = st.select_slider(
    "Months (inclusive)",
    options=months,
    value=(months[0], months[0]),
)

# Apply the same date range to the complete data and the national series.
month_values = frame["date"].dt.to_period("M").astype(str)
selected_rows = frame.loc[month_values.between(*selected_months)].copy()
subset = national_series(selected_rows)
if subset.empty:
    st.warning("No records in the selected months.")
    st.stop()

if selected_column == "All numeric columns":
    # Seven small time-series panels preserve each field's original units.
    order = ["fill_level", "previous_week_fill_level", "stored_energy_twh",
             "capacity_twh", "fill_level_change", "iso_week", "iso_year"]
    colors = sns.color_palette("deep", len(order))
    figure, axes = plt.subplots(4, 2, figsize=(12, 11), sharex=True)
    for axis, column, color in zip(axes.flat, order, colors):
        sns.lineplot(data=subset, x="date", y=column, estimator=None,
                     errorbar=None, marker="o" if len(subset) <= 12 else None,
                     linewidth=1.5, color=color, ax=axis)
        axis.set(title=PLOT_LABELS[column][0], xlabel="", ylabel=PLOT_LABELS[column][1])
        sns.despine(ax=axis)
    axes.flat[-1].axis("off")
    figure.suptitle("All numeric columns — separate scales", fontsize=15)
    figure.autofmt_xdate()
    figure.tight_layout()
    st.info("Each panel has its own vertical scale. ISO year and week identify time; they are not reservoir measurements.")
elif selected_column in NUMERIC_COLUMNS:
    figure, axis = plt.subplots(figsize=(10, 4.7))
    sns.lineplot(data=subset, x="date", y=selected_column, estimator=None,
                 errorbar=None, marker="o" if len(subset) <= 12 else None,
                 linewidth=2, color="#2563a6", ax=axis)
    axis.set(title=PLOT_LABELS[selected_column][0], xlabel="Date",
             ylabel=PLOT_LABELS[selected_column][1])
    figure.autofmt_xdate()
    sns.despine(ax=axis)
    figure.tight_layout()
    if selected_column in ("iso_year", "iso_week"):
        st.info("This is a calendar identifier over time, not a reservoir measurement.")
elif selected_column == "date":
    # Date is the x-coordinate, so dots show when national reports exist.
    figure, axis = plt.subplots(figsize=(10, 3.4))
    sns.scatterplot(x=subset["date"], y=[1] * len(subset), s=65,
                    color="#2563a6", ax=axis)
    axis.set(title="Reporting dates", xlabel="Date", ylabel="")
    axis.set(yticks=[], ylim=(0.8, 1.2))
    figure.autofmt_xdate()
    sns.despine(ax=axis, left=True)
    figure.tight_layout()
elif selected_column in ("area_type", "area_number"):
    # Geographic identifiers are categories; count all areas in the date range.
    counts = (selected_rows[selected_column].astype(str).value_counts()
              .rename_axis("category").reset_index(name="rows"))
    figure, axis = plt.subplots(figsize=(9, 4))
    sns.barplot(data=counts, x="category", y="rows", color="#3178a8",
                errorbar=None, ax=axis)
    axis.set(title=f"Records by {selected_column}", xlabel=selected_column,
             ylabel="CSV rows")
    sns.despine(ax=axis)
    figure.tight_layout()
    st.info("Category counts include every geographic area in the selected months.")
else:
    # Year 0001 in the source means that no publication date was supplied.
    parsed = pd.to_datetime(selected_rows["next_publication_date"],
                            format="%Y-%m-%dT%H:%M:%S", errors="coerce")
    counts = pd.DataFrame({"status": ["Date supplied", "No date (0001)"],
                           "rows": [parsed.notna().sum(), parsed.isna().sum()]})
    figure, axis = plt.subplots(figsize=(9, 4))
    sns.barplot(data=counts, x="status", y="rows", color="#3178a8",
                errorbar=None, ax=axis)
    axis.set(title="Next publication date availability", xlabel="", ylabel="CSV rows")
    sns.despine(ax=axis)
    figure.tight_layout()
    st.info("Status counts include every geographic area in the selected months.")

st.pyplot(figure, width="stretch")
plt.close(figure)
st.caption(f"{len(subset)} weekly records from Norway total, {selected_months[0]} to {selected_months[1]}.")
