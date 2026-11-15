"""Weekly weather history for every reservoir area, read from MongoDB (prepared in the Part 4 notebook).

The Map, Weather vs. reservoir and Forecast pages need many years of weather for all areas. That is
too many Open-Meteo calls to download live (the free quota is 10,000 calls per day, and ten years at
one location cost about 280 calls). The Part 4 notebook therefore downloads daily ERA5 values once for
6 locations per area (one per ERA5 grid cell), sums or averages them per ISO week in Norwegian time and
stores the result in MongoDB. Each document is one area and one week:

    {"area_type": "EL", "area_number": 3, "week": <Sunday that ends the ISO week>,
     "temperature": -2.1, "precipitation": 31.4, "snowfall": 12.0}

The Weather outliers page still downloads hourly weather directly from Open-Meteo (weather_api.py).
"""

import pandas as pd
from pymongo.errors import PyMongoError
import streamlit as st

from src.utils.flows_db import MissingSecrets, get_database


COLLECTION = "weather_weekly"
CACHE_SECONDS = 60 * 60  # the stored data only change when the notebook is re-run
# Weekly variables with labels and units (temperature is a mean, the others are weekly sums).
WEEKLY_VARIABLES = {
    "temperature": ("Mean temperature", "°C"),
    "precipitation": ("Precipitation", "mm per week"),
    "snowfall": ("Snowfall", "cm per week"),
}


@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Reading weekly weather from MongoDB…")
def load_weekly_weather() -> pd.DataFrame:
    """All weekly weather documents (about 5,000 rows: 9 areas × 10 years of weeks)."""
    rows = list(get_database()[COLLECTION].find({}, {"_id": 0}))
    frame = pd.DataFrame(rows)
    # PyMongo returns the week label as a naive datetime (midnight); it is a date, not a moment.
    frame["week"] = pd.to_datetime(frame["week"])
    return frame.sort_values(["area_type", "area_number", "week"]).reset_index(drop=True)


def weekly_weather_or_stop() -> pd.DataFrame:
    """Load the weekly weather; if MongoDB cannot be read, show a short message and stop the page."""
    try:
        frame = load_weekly_weather()
    except MissingSecrets as error:
        st.error(f"MongoDB is not configured: {error}")
        st.stop()
    except PyMongoError as error:  # wrong password, IP not allowed in Atlas, paused cluster, network ...
        st.error(f"Could not read the weekly weather from MongoDB ({type(error).__name__}). "
                 "Check the connection string and that Atlas Network Access allows this app.")
        st.stop()
    if frame.empty:
        st.warning("The weekly weather collection is empty. Run section 5 of the Part 4 notebook to fill it.")
        st.stop()
    return frame


def area_weather(frame: pd.DataFrame, area_type: str, area_number: int) -> pd.DataFrame:
    """Weekly weather of one area, indexed by the Sunday that ends each week."""
    rows = frame.loc[(frame["area_type"] == area_type) & (frame["area_number"] == area_number)]
    return rows.set_index("week")[list(WEEKLY_VARIABLES)].sort_index()


def area_weather_or_stop(frame: pd.DataFrame, area_type: str, area_number: int, name: str) -> pd.DataFrame:
    """Weekly weather of one area; if MongoDB has none for it, show a short message and stop the page."""
    weather = area_weather(frame, area_type, area_number)
    if weather.empty:
        st.warning(f"There is no weekly weather for {name} in MongoDB yet. "
                   "Run section 5 of the Part 4 notebook to add it.")
        st.stop()
    return weather
