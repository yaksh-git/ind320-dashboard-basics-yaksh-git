"""Start – Map: NVE's reservoir areas on an interactive map; a click chooses the area for the other pages.

- Outlines: the GeoJSON polygons of the price areas (EL) and watercourse regions (VASS), made from
  NVE's map services in the Part 3 notebook (data/regions/areas.geojson, clipped to land).
- Colour: the fill level (NVE API) or a weather property (weekly ERA5 from MongoDB), as the last week
  or the mean of the chosen time period. The colours are semi-transparent so the base map shows through.
- Time: the period slider is shared with the Weather vs. reservoir and Forecast pages (session state).
- Click: clicking an area gives it a thick dark outline and stores it as the chosen area
  (src/utils/controls.py), so the analysis pages open with that area.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.controls import chosen_area, period_slider, select_area
from src.utils.nve_api import load_areas, load_data, nve_or_stop
from src.utils.ui import NAVY, page_header, style_figure
from src.utils.weather_history import WEEKLY_VARIABLES, area_weather, weekly_weather_or_stop


AREAS_FILE = Path(__file__).resolve().parents[2] / "data" / "regions" / "areas.geojson"
COLOUR_BY = {
    "fill_EL": "Fill level · price areas (EL)",
    "fill_VASS": "Fill level · watercourse regions (VASS)",
    "weather": "Weather property",
}
STATISTICS = ["Last week of the period", "Mean over the period"]
# One colour scale per property: blue for water, purple for snow, red–blue for temperature.
COLOUR_SCALES = {"fill_level": "Blues", "temperature": "RdBu_r", "precipitation": "Blues",
                 "snowfall": "Purples"}
ANALYSIS_PAGES = [("src/pages/fill_analysis.py", "Fill-level analysis"),
                  ("src/pages/correlation.py", "Weather vs. reservoir"),
                  ("src/pages/weather_outliers.py", "Weather outliers"),
                  ("src/pages/forecast.py", "Reservoir forecast")]


@st.cache_data
def load_geojson() -> dict:
    """The area polygons as GeoJSON, each feature with an id like "EL3" that Plotly can match."""
    geojson = json.loads(AREAS_FILE.read_text(encoding="utf-8"))
    for feature in geojson["features"]:
        properties = feature["properties"]
        feature["id"] = f"{properties['area_type']}{properties['area_number']}"
    return geojson


def area_features(area_type: str) -> list[dict]:
    """The GeoJSON features of one area type (EL or VASS)."""
    return [f for f in load_geojson()["features"] if f["properties"]["area_type"] == area_type]


def choose_colouring() -> tuple[str, str, str]:
    """Controls for what colours the map; return (area type, value column, statistic)."""
    left, middle, right = st.columns([2, 1.2, 1.4])
    colour_by = left.radio("Colour by", list(COLOUR_BY), format_func=COLOUR_BY.get, horizontal=True)
    if colour_by == "weather":
        column = middle.selectbox("Weather property", list(WEEKLY_VARIABLES),
                                  format_func=lambda name: WEEKLY_VARIABLES[name][0])
        area_type = middle.radio("Areas", ["EL", "VASS"], horizontal=True,
                                 format_func={"EL": "Price areas", "VASS": "Watercourse regions"}.get)
    else:
        column, area_type = "fill_level", colour_by.split("_")[1]
    statistic = right.radio("Statistic", STATISTICS, help="The value of the period's last week, or the "
                            "mean of all weeks in the period.")
    return area_type, column, statistic


def fill_values(frame: pd.DataFrame, area_type: str, period: tuple, statistic: str) -> pd.Series:
    """Fill level per area number for the period (percent): last week or mean of the weeks."""
    rows = frame.loc[(frame["area_type"] == area_type) & frame["date"].between(*period)]
    per_area = rows.groupby("area_number")["fill_level"]
    values = per_area.last() if statistic == STATISTICS[0] else per_area.mean()
    return values * 100


def weather_values(weather: pd.DataFrame, area_type: str, column: str, period: tuple,
                   statistic: str) -> pd.Series:
    """One weather property per area number for the period: last week or the mean week."""
    values = {}
    for number in sorted(weather.loc[weather["area_type"] == area_type, "area_number"].unique()):
        series = area_weather(weather, area_type, number)[column].loc[period[0]:period[1]]
        values[number] = series.iloc[-1] if statistic == STATISTICS[0] else series.mean()
    return pd.Series(values)


def apply_click(map_key: str, area_type: str) -> None:
    """If an area was clicked on the map (stored under map_key), make it the chosen area."""
    event = st.session_state.get(map_key)
    points = event.selection.points if event else []
    if points:
        # "location" is the feature id, e.g. "EL3": the type followed by the number.
        select_area(area_type, int(points[0]["location"][len(area_type):]))


def map_figure(area_type: str, values: pd.Series, column: str, label: str, chosen: int | None) -> go.Figure:
    """Choropleth map of one area type; the chosen area gets a thick dark outline."""
    features = area_features(area_type)
    ids = [f["id"] for f in features]
    names = [f["properties"]["name"] for f in features]
    numbers = [f["properties"]["area_number"] for f in features]
    z = [values.get(number) for number in numbers]
    widths = [4 if number == chosen else 0.8 for number in numbers]
    figure = go.Figure(go.Choroplethmap(
        geojson={"type": "FeatureCollection", "features": features}, locations=ids, z=z,
        featureidkey="id", text=names, colorscale=COLOUR_SCALES[column], marker_opacity=0.55,
        marker_line_width=widths, marker_line_color=NAVY, colorbar={"title": {"text": label}},
        hovertemplate="<b>%{text}</b><br>%{z:.1f}<extra>Click to choose</extra>"))
    figure.update_layout(map={"style": "carto-positron", "center": {"lat": 65.0, "lon": 15.0}, "zoom": 3.4},
                         height=620, margin={"l": 0, "r": 0, "t": 10, "b": 0}, clickmode="event+select")
    return figure


def show_chosen_area(area_type: str, chosen: int | None, values: pd.Series, label: str) -> None:
    """Card with the chosen area, its value and links to the analysis pages that will use it."""
    with st.container(border=True):
        st.caption("Chosen area")
        if chosen is None:
            st.write("Click an area on the map.")
            return
        name = f"NO {chosen}" if area_type == "EL" else f"VASS{chosen}"
        st.subheader(name)
        if chosen in values.index:
            st.metric(label, f"{values[chosen]:.1f}")
        st.caption("Open an analysis page with this area:")
        for page, title in ANALYSIS_PAGES:
            st.page_link(page, label=title)


def render_page() -> None:
    """Draw the page: colouring controls, the shared time period, the map and the chosen-area card."""
    page_header("Start", "Map and area selection",
                "Colour NVE's reservoir areas by fill level or weather, and click an area to choose it "
                "for the analysis pages.")
    frame = nve_or_stop(load_data)  # weekly fill level, cached (src/utils/nve_api.py)
    nve_or_stop(load_areas)
    with st.container(border=True):
        area_type, column, statistic = choose_colouring()
        weeks = sorted(frame["date"].unique())
        period = period_slider([pd.Timestamp(week) for week in weeks])

    if column == "fill_level":
        values, label = fill_values(frame, area_type, period, statistic), "Fill level (%)"
    else:
        weather = weekly_weather_or_stop()
        values = weather_values(weather, area_type, column, period, statistic)
        label = f"{WEEKLY_VARIABLES[column][0]} ({WEEKLY_VARIABLES[column][1]})"

    map_key = f"area_map_{area_type}"  # one selection per area type
    apply_click(map_key, area_type)
    chosen_type, chosen_number = chosen_area()
    chosen = chosen_number if chosen_type == area_type else None

    left, right = st.columns([3, 1])
    with left:
        figure = style_figure(map_figure(area_type, values, column, label, chosen))
        st.plotly_chart(figure, width="stretch", theme=None, key=map_key, on_select="rerun",
                        selection_mode="points", config={"displaylogo": False, "scrollZoom": True})
    with right:
        show_chosen_area(area_type, chosen, values, label)
    st.caption(f"{statistic} {period[0]:%d %b %Y} – {period[1]:%d %b %Y}. The period is shared with the "
               "Weather vs. reservoir and Forecast pages. Scroll to zoom the map; hover for values.")


render_page()
