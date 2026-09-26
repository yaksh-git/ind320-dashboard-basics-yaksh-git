"""Shared loading and naming rules for the reservoir data."""

from pathlib import Path

import pandas as pd
import streamlit as st


DATA_PATH = Path(__file__).parent / "reservoirs.csv"

# The source file uses Norwegian field names. Keep a single translation for all pages.
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


@st.cache_data
def load_data() -> pd.DataFrame:
    """Read the local CSV once per file version for faster Streamlit reruns."""
    frame = pd.read_csv(DATA_PATH).rename(columns=COLUMN_NAMES)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    # Year 0001 denotes an unknown publication date in the source file.
    frame["area_number"] = frame["area_number"].astype("Int64")
    return frame.sort_values(["date", "area_type", "area_number"]).reset_index(drop=True)


def national_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Use the source's national aggregate (NO, area 0) for time-series plots."""
    return frame.loc[(frame["area_type"] == "NO") & (frame["area_number"] == 0)].copy()

