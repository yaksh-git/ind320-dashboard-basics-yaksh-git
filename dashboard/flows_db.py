"""Read the curated cross-border flow data from MongoDB for the Streamlit app.

Pipeline (see the Part 2 notebook): ENTSO-E API -> Cassandra (written with Spark)
-> Spark selects and aggregates the relevant columns -> MongoDB -> this app.
Each MongoDB document is one hour of physical flow on one link in one direction:

    {"neighbour": "Sweden", "link": "NO1-SE3", "from_area": "SE3", "to_area": "NO1",
     "direction": "import", "time": <UTC hour start>, "year": 2025, "month": 1,
     "energy_mwh": 512.0}

year and month follow Norwegian local time, so January starts at midnight in Oslo.
"""

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConfigurationError
import streamlit as st


COLLECTION = "cross_border_flows_hourly"
CACHE_SECONDS = 60 * 60  # The stored data only change when the notebook is re-run.
DIRECTION_LABELS = {"import": "Into Norway (import)", "export": "Out of Norway (export)"}


class MissingSecrets(RuntimeError):
    """Raised when the MongoDB connection string has not been configured."""


@st.cache_resource
def get_collection():
    """Create one MongoDB client per app process and return the flow collection.

    The connection string is read from st.secrets: locally from .streamlit/secrets.toml
    (ignored by Git) and on Streamlit Community Cloud from the app's Secrets settings.
    """
    try:
        settings = st.secrets["mongo"]
        uri = settings["uri"]
    except (KeyError, FileNotFoundError) as error:
        raise MissingSecrets("Add a [mongo] section with 'uri' to the Streamlit secrets.") from error
    # A real connection string starts with mongodb:// or mongodb+srv:// (not the placeholder text).
    if not uri.startswith(("mongodb://", "mongodb+srv://")):
        raise MissingSecrets("The MongoDB 'uri' in the Streamlit secrets is not a connection string.")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    except ConfigurationError as error:
        raise MissingSecrets("The MongoDB 'uri' in the Streamlit secrets is not valid.") from error
    return client[settings.get("database", "ind320")][COLLECTION]


@st.cache_data(ttl=CACHE_SECONDS)
def load_options() -> dict:
    """Connections (neighbour countries) and years available in the database."""
    collection = get_collection()
    return {
        "neighbours": sorted(collection.distinct("neighbour")),
        "years": sorted(collection.distinct("year")),
    }


@st.cache_data(ttl=CACHE_SECONDS)
def load_flows_for(neighbour: str) -> pd.DataFrame:
    """Every link/direction pair on one connection, e.g. NO1 -> SE3 and SE3 -> NO1."""
    pipeline = [
        {"$match": {"neighbour": neighbour}},
        {"$group": {"_id": {"from": "$from_area", "to": "$to_area", "direction": "$direction"}}},
    ]
    rows = [group["_id"] for group in get_collection().aggregate(pipeline)]
    flows = pd.DataFrame(rows).rename(columns={"from": "from_area", "to": "to_area"})
    flows["flow"] = flows["from_area"] + " → " + flows["to_area"]
    # Exports first, then imports, each sorted by link name.
    return flows.sort_values(["direction", "flow"], ascending=[True, True]).reset_index(drop=True)


@st.cache_data(ttl=CACHE_SECONDS)
def load_year_totals(neighbour: str, year: int) -> pd.DataFrame:
    """Total energy into and out of Norway for one connection and year.

    MongoDB sums the ~8,760 hourly documents per link and direction itself, so only
    two small result rows travel over the network instead of every hour.
    """
    pipeline = [
        {"$match": {"neighbour": neighbour, "year": year}},
        {"$group": {"_id": "$direction", "energy_mwh": {"$sum": "$energy_mwh"},
                    "hours": {"$sum": 1}}},
    ]
    rows = list(get_collection().aggregate(pipeline))
    totals = pd.DataFrame(rows, columns=["_id", "energy_mwh", "hours"])
    return totals.rename(columns={"_id": "direction"})


@st.cache_data(ttl=CACHE_SECONDS)
def load_month(neighbour: str, year: int, month: int) -> pd.DataFrame:
    """Hourly flows for every link and direction on one connection in one month."""
    query = {"neighbour": neighbour, "year": year, "month": month}
    projection = {"_id": 0, "time": 1, "from_area": 1, "to_area": 1,
                  "direction": 1, "energy_mwh": 1}
    frame = pd.DataFrame(list(get_collection().find(query, projection)))
    if frame.empty:
        return frame
    # PyMongo returns naive UTC datetimes; show them in Norwegian time.
    frame["time"] = pd.to_datetime(frame["time"], utc=True).dt.tz_convert("Europe/Oslo")
    frame["flow"] = frame["from_area"] + " → " + frame["to_area"]
    return frame.sort_values(["flow", "time"]).reset_index(drop=True)
