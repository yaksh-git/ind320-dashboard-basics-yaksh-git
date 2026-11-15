"""Exchange rates (EUR/NOK and USD/NOK) directly from Norges Bank's open data API.

Norges Bank publishes one rate per business day (no weekends or Norwegian bank holidays),
fixed at about 14:15 CET (the ECB concertation). The rates have a date but no time or time zone.
The app uses them as weekly means, matching NVE's weeks (ISO weeks that end on Sunday).
Same function as download_exchange_rates() in the Part 4 notebook.
"""

from io import StringIO

import pandas as pd
import requests
import streamlit as st


NB_URL = "https://data.norges-bank.no/api/data/EXR/B.{currencies}.NOK.SP"
CURRENCIES = ("EUR", "USD")
CACHE_SECONDS = 12 * 60 * 60  # one new rate per business day, so twice a day is plenty


def download_exchange_rates(start: str, end: str, currencies: tuple[str, ...] = CURRENCIES) -> pd.DataFrame:
    """Daily rates (NOK per unit of currency) between two dates, one column per currency."""
    url = NB_URL.format(currencies="+".join(currencies))
    params = {"format": "csv", "startPeriod": start, "endPeriod": end, "locale": "en"}
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()  # Stop with a clear error on HTTP 4xx/5xx.
    # The CSV is semicolon-separated: one row per currency and business day.
    rows = pd.read_csv(StringIO(response.text), sep=";")
    rows["TIME_PERIOD"] = pd.to_datetime(rows["TIME_PERIOD"], format="%Y-%m-%d")
    rates = rows.pivot(index="TIME_PERIOD", columns="BASE_CUR", values="OBS_VALUE")
    return rates.rename_axis(index="date", columns=None)


def weekly_rates(daily: pd.DataFrame) -> pd.DataFrame:
    """Mean rate per ISO week, labelled by the Sunday that ends the week (as NVE's dato_Id)."""
    return daily.resample("W-SUN").mean()


@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Downloading exchange rates from Norges Bank…")
def load_weekly_rates(start: str, end: str) -> pd.DataFrame:
    """Weekly EUR/NOK and USD/NOK between two dates (cached for twelve hours)."""
    return weekly_rates(download_exchange_rates(start, end))
