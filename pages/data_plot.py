"""Interactive plot with column and month selection."""

import matplotlib.pyplot as plt
import streamlit as st

from data_utils import NUMERIC_COLUMNS, load_data, national_series


st.title("Reservoir data plot")
series = national_series(load_data())
months = series["date"].dt.to_period("M").astype(str).unique().tolist()

# The source has several geographic series for each week. We use the supplied
# national aggregate to avoid drawing unrelated areas as one connected line.
selected_column = st.selectbox("CSV column", ["All numeric columns", *series.columns.tolist()])
selected_months = st.select_slider(
    "Months (inclusive)",
    options=months,
    value=(months[0], months[0]),
)
month_values = series["date"].dt.to_period("M").astype(str)
subset = series.loc[month_values.between(*selected_months)].copy()

if subset.empty:
    st.warning("No records in the selected months.")
    st.stop()

figure, axis = plt.subplots(figsize=(10, 4.5))
if selected_column == "All numeric columns":
    # Normalize each numeric column to 0–1 because units and ranges differ.
    # Constant columns are omitted because their normalized trend is undefined.
    normalized = subset[NUMERIC_COLUMNS].copy()
    denominators = normalized.max() - normalized.min()
    varying = denominators[denominators > 0].index
    normalized = (normalized[varying] - normalized[varying].min()) / denominators[varying]
    for column in varying:
        axis.plot(subset["date"], normalized[column], marker="o", label=column)
    axis.set_ylabel("Normalized value (0–1)")
    axis.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
else:
    # Datetimes and categories can be selected too. For date, the chart shows
    # records per week; category fields are shown as a dated sequence.
    if selected_column == "date":
        weekly = subset.groupby("date").size()
        axis.plot(weekly.index, weekly.values, marker="o")
        axis.set_ylabel("Records per date")
    elif selected_column in NUMERIC_COLUMNS:
        axis.plot(subset["date"], subset[selected_column], marker="o")
        axis.set_ylabel(selected_column)
    else:
        axis.plot(subset["date"], subset[selected_column].astype(str), marker="o")
        axis.set_ylabel(selected_column)

axis.set_title(f"{selected_column} — Norway total, {selected_months[0]} to {selected_months[1]}")
axis.set_xlabel("Date")
axis.grid(alpha=0.25)
figure.autofmt_xdate()
st.pyplot(figure, width="stretch")
plt.close(figure)
st.caption(f"{len(subset)} weekly records shown from the Norway total series (NO, area 0).")
