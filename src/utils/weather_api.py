"""Download hourly ERA5 weather from Open-Meteo for the Magasinstatistikk areas.

The Part 3 notebook drew 1000 random locations inside each area (NVE polygons, land only). Part 4
stores them as GeoJSON (data/regions/sample_points.geojson, one MultiPoint per area) instead of a CSV
file, as peer review 3 suggested. After the teacher's feedback on Part 3 the app no longer takes 20 random
locations: it groups all 1000 points into 20 clusters and downloads one ERA5 cell per cluster, weighted by
the cluster's share of the points (src/utils/locations.py). The weighted hourly mean is much closer to the
mean of all 1000 points for the same number of Open-Meteo calls.
"""

import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from src.utils.locations import representative_cells, weighted_area_mean


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
POINTS_FILE = Path(__file__).resolve().parents[2] / "data" / "regions" / "sample_points.geojson"
N_LOCATIONS = 20  # one year at 20 locations stays well inside Open-Meteo's free daily quota
FIRST_YEAR = 1995  # first year of NVE's reservoir statistics

# Hourly variables with labels and Open-Meteo's default units (used on the plot axes).
VARIABLES = {
    "temperature_2m": ("Temperature (2 m)", "°C"),
    "precipitation": ("Precipitation", "mm per hour"),
    "rain": ("Rain", "mm per hour"),
    "snowfall": ("Snowfall", "cm per hour"),
    "wind_speed_10m": ("Wind speed (10 m)", "km/h"),
}


@st.cache_data
def load_points() -> pd.DataFrame:
    """The 1000 random locations per area from the notebook (area_type, area_number, lon, lat)."""
    features = json.loads(POINTS_FILE.read_text(encoding="utf-8"))["features"]
    # One row per point: each feature is one area, and its MultiPoint holds that area's 1000 points.
    return pd.DataFrame([{"area_type": f["properties"]["area_type"], "area_number": f["properties"]["area_number"],
                          "lon": lon, "lat": lat}
                         for f in features for lon, lat in f["geometry"]["coordinates"]])


def area_locations(area_type: str, area_number: int) -> pd.DataFrame:
    """N_LOCATIONS representative ERA5 cells of the area with weights (columns lat, lon, weight)."""
    points = load_points()
    points = points.loc[(points["area_type"] == area_type) & (points["area_number"] == area_number)]
    return representative_cells(points, N_LOCATIONS)


def request_weather(locations: pd.DataFrame, start: str, end: str) -> list[dict]:
    """One Open-Meteo request for all locations; returns one JSON object per location."""
    params = {
        "latitude": ",".join(map(str, locations["lat"])),
        "longitude": ",".join(map(str, locations["lon"])),
        "start_date": start, "end_date": end,
        "hourly": ",".join(VARIABLES), "models": "era5",
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=300)
    response.raise_for_status()  # Stop with a clear error on HTTP 4xx/5xx (e.g. 429 = quota used).
    answer = response.json()
    return answer if isinstance(answer, list) else [answer]  # one location gives one object


# ERA5 history does not change, so the result is kept until the app restarts (max 20 area-years).
@st.cache_data(max_entries=20, show_spinner="Downloading hourly weather from Open-Meteo (ERA5)…")
def load_weather(area_type: str, area_number: int, year: int) -> pd.DataFrame:
    """Hourly weighted area mean of every variable in VARIABLES for one calendar year (UTC index)."""
    locations = area_locations(area_type, area_number)
    answer = request_weather(locations, f"{year}-01-01", f"{year}-12-31")
    # Open-Meteo answers in the same order as the locations, so the position identifies the location.
    per_location = pd.concat([pd.DataFrame(item["hourly"]).assign(location=i) for i, item in enumerate(answer)],
                             ignore_index=True)
    per_location["time"] = pd.to_datetime(per_location["time"], format="%Y-%m-%dT%H:%M", utc=True)
    return weighted_area_mean(per_location, locations["weight"], "time", list(VARIABLES))


def weather_or_stop(area_type: str, area_number: int, year: int) -> pd.DataFrame:
    """Load the weather; if Open-Meteo cannot be reached, show a short message and stop the page."""
    try:
        return load_weather(area_type, area_number, year)
    except requests.RequestException as error:  # timeout, no network, HTTP 4xx/5xx from Open-Meteo
        st.error(f"Could not download weather from Open-Meteo ({type(error).__name__}). "
                 "The free API has a daily limit; please try again later.")
        st.stop()
