"""Load NVE reservoir statistics (Magasinstatistikk) directly from NVE's open API.

Part 1 read a fixed CSV snapshot. Part 2 replaces that file with requests to
https://biapi.nve.no/magasinstatistikk, so every page shows the latest weekly report.
The API needs no key and has no query parameters: HentOffentligData returns the full history.
"""

from collections.abc import Callable

import pandas as pd
import requests
import streamlit as st


API_URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"
# NVE publishes once a week (Wednesdays), so a few downloads a day are plenty.
CACHE_SECONDS = 6 * 60 * 60

# The API uses the same Norwegian field names as the Part 1 CSV. One translation for all pages.
COLUMN_NAMES = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "fill_level",
    "kapasitet_TWh": "capacity_twh",
    "fylling_TWh": "stored_energy_twh",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "previous_week_fill_level",
    "endring_fyllingsgrad": "fill_level_change",
}

NUMERIC_COLUMNS = [
    "iso_year",
    "iso_week",
    "fill_level",
    "capacity_twh",
    "stored_energy_twh",
    "previous_week_fill_level",
    "fill_level_change",
]

# Human-readable labels and units keep the plots understandable.
PLOT_LABELS = {
    "iso_year": ("ISO year", "Year"),
    "iso_week": ("ISO week", "Week number"),
    "fill_level": ("Reservoir fill level", "Fraction full"),
    "capacity_twh": ("Reservoir capacity", "TWh"),
    "stored_energy_twh": ("Stored energy", "TWh"),
    "previous_week_fill_level": ("Previous-week fill level", "Fraction full"),
    "fill_level_change": ("Weekly change in fill level", "Fraction points"),
}

# The three kinds of area in the API (omrType), used by the radio buttons.
AREA_TYPES = {
    "EL": "Electricity price areas (EL)",
    "NO": "Norway total (NO)",
    "VASS": "Watercourse regions (VASS)",
}


def get_json(endpoint: str) -> list[dict]:
    """Call one NVE endpoint and return the decoded JSON body (a list of records)."""
    response = requests.get(
        f"{API_URL}/{endpoint}", headers={"Accept": "application/json"}, timeout=60
    )
    response.raise_for_status()  # Stop with a clear error on HTTP 4xx/5xx.
    return response.json()


@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Downloading reservoir statistics from NVE…")
def load_data() -> pd.DataFrame:
    """Download all weekly records once and reuse them across pages and reruns."""
    frame = pd.DataFrame(get_json("HentOffentligData")).rename(columns=COLUMN_NAMES)
    # dato_Id is the last day (Sunday) of the ISO week that the measurement describes.
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d")
    frame["area_number"] = frame["area_number"].astype("Int64")
    # next_publication_date stays text: year 0001 means "no date" and is outside pandas' range.
    return frame.sort_values(["date", "area_type", "area_number"]).reset_index(drop=True)


@st.cache_data(ttl=CACHE_SECONDS)
def load_areas() -> pd.DataFrame:
    """Names and descriptions of every area the API defines (endpoint HentOmråder)."""
    # The response is a list with one object holding the land, elspot and vassdrag lists.
    groups = get_json("HentOmråder")[0]
    rows = [area for areas in groups.values() for area in areas]
    return pd.DataFrame(rows).rename(columns={
        "navn": "name",
        "navn_langt": "long_name",
        "beskrivelse": "description",
        "omrType": "area_type",
        "omrnr": "area_number",
    })


def nve_or_stop(loader: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    """Run an NVE loader; if the API cannot be reached, show a short message instead of a traceback."""
    try:
        return loader()
    except requests.RequestException as error:  # timeout, no network, HTTP 4xx/5xx from NVE
        st.error(f"Could not download data from the NVE API ({type(error).__name__}). "
                 "Please try again in a minute.")
        st.stop()


def national_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Use the source's national aggregate (NO, area 0) for time-series plots."""
    return frame.loc[(frame["area_type"] == "NO") & (frame["area_number"] == 0)].copy()


def month_options(frame: pd.DataFrame) -> list[str]:
    """All months with data, as "YYYY-MM" text, oldest first (options for the interval slider)."""
    return frame["date"].dt.to_period("M").astype(str).unique().tolist()


def select_interval(frame: pd.DataFrame, first_month: str, last_month: str) -> pd.DataFrame:
    """Rows from the first to the last chosen month, both included ("YYYY-MM" text compares in order)."""
    months = frame["date"].dt.to_period("M").astype(str)
    return frame.loc[months.between(first_month, last_month)].copy()


def areas_of_type(frame: pd.DataFrame, areas: pd.DataFrame, area_type: str) -> pd.DataFrame:
    """Rows of one area type, with NVE's own area name (e.g. "NO 1", "VASS1") in a new "area" column."""
    subset = frame.loc[frame["area_type"] == area_type].copy()
    names = areas.set_index(["area_type", "area_number"])["name"].to_dict()
    subset["area"] = [names.get((kind, int(number)), f"{kind} {number}")
                      for kind, number in zip(subset["area_type"], subset["area_number"])]
    return subset
