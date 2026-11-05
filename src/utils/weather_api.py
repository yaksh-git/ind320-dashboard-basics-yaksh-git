"""Download hourly ERA5 weather from Open-Meteo for the Magasinstatistikk areas.

The Part 3 notebook drew 1000 random locations inside each area (NVE polygons, land only) and
saved them to data/regions/sample_points.csv. The app downloads a random subset of these locations
for the chosen area and year, and averages them per hour, exactly like download_weather() in the notebook.
"""

from pathlib import Path

import pandas as pd
import requests
import streamlit as st


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
POINTS_FILE = Path(__file__).resolve().parents[2] / "data" / "regions" / "sample_points.csv"
N_LOCATIONS = 20  # one year at 20 locations stays well inside Open-Meteo's free daily quota
SEED = 320        # same random subset as in the notebook
ERA5_GRID = 0.25  # degrees; points in the same grid cell would return identical values
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
    return pd.read_csv(POINTS_FILE)


def area_locations(area_type: str, area_number: int) -> pd.DataFrame:
    """Random subset of the area's locations, at most one per ERA5 grid cell (columns lat, lon)."""
    points = load_points()
    points = points.loc[(points["area_type"] == area_type) & (points["area_number"] == area_number)]
    # Round to the ERA5 grid so that two points in the same cell are downloaded only once.
    cells = points.assign(lat=(points["lat"] / ERA5_GRID).round() * ERA5_GRID,
                          lon=(points["lon"] / ERA5_GRID).round() * ERA5_GRID)
    cells = cells.drop_duplicates(["lat", "lon"])
    return cells.sample(min(N_LOCATIONS, len(cells)), random_state=SEED)[["lat", "lon"]]


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
    """Hourly area mean of every variable in VARIABLES for one calendar year (UTC index)."""
    answer = request_weather(area_locations(area_type, area_number), f"{year}-01-01", f"{year}-12-31")
    per_location = pd.concat([pd.DataFrame(item["hourly"]) for item in answer], ignore_index=True)
    per_location["time"] = pd.to_datetime(per_location["time"], format="%Y-%m-%dT%H:%M", utc=True)
    return per_location.groupby("time")[list(VARIABLES)].mean()


def weather_or_stop(area_type: str, area_number: int, year: int) -> pd.DataFrame:
    """Load the weather; if Open-Meteo cannot be reached, show a short message and stop the page."""
    try:
        return load_weather(area_type, area_number, year)
    except requests.RequestException as error:  # timeout, no network, HTTP 4xx/5xx from Open-Meteo
        st.error(f"Could not download weather from Open-Meteo ({type(error).__name__}). "
                 "The free API has a daily limit; please try again later.")
        st.stop()
