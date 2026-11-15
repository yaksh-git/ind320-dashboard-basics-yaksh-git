"""Forecast the weekly reservoir fill level with the River framework (online machine learning).

Two models, both trained one week at a time (River's learn_one) and forecast dynamically, i.e. each
forecast week is built on the forecasts of the weeks before it, not on observed values:

- "Lag regression": a linear regression that predicts next week's change in fill level from the
  current level, the last p changes, the change in the same week last year, the time of year
  (sine/cosine terms) and the chosen exogenous variables. The level is the sum of the changes.
- "SNARIMAX": River's seasonal ARIMA with exogenous variables (p, d, q and seasonal sp, sd, sq with
  a 52-week season). Its regression is also fitted online with stochastic gradient descent (SGD).

Exogenous variables are weekly weather (MongoDB, prepared in the Part 4 notebook) and the EUR/NOK
exchange rate (Norges Bank). The future weather is unknown, so it is replaced by the mean of the same
ISO week in the training years (climatology); the exchange rate keeps its last value.
Confidence bands (bonus task): two extra models are trained with the quantile (pinball) loss
(optim.losses.Quantile), one for the lower and one for the upper quantile.
The same function is developed and tested in section 7 of the Part 4 notebook.
"""

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from river import linear_model, optim, preprocessing, time_series


WEEKS_PER_YEAR = 52
WARM_UP = WEEKS_PER_YEAR + 2  # weeks before the training period that the lag features need
SNOWPACK_WEEKS = 26           # snowfall summed over half a year approximates the snow that can melt
MODELS = ("Lag regression", "SNARIMAX")
# Exogenous variables the user can choose: weekly weather (MongoDB) and the exchange rate (Norges Bank).
EXOGENOUS = {
    "temperature": "Mean temperature (°C)",
    "precipitation": "Precipitation (mm per week)",
    "snowfall": "Snowfall (cm per week)",
    "snowpack": "Snowfall over the last 26 weeks (cm)",
    "eur_nok": "EUR/NOK exchange rate",
}


@dataclass(frozen=True)
class Settings:
    """All model settings. The defaults are the best settings from the notebook tests (section 7)."""
    model: str = "Lag regression"
    history_years: int = 8      # length of the training period (years of weeks)
    horizon: int = 26           # weeks to forecast
    p: int = 2                  # number of recent weekly changes (lag regression) / AR order (SNARIMAX)
    d: int = 0                  # SNARIMAX: differencing
    q: int = 0                  # SNARIMAX: moving-average order
    sp: int = 1                 # seasonal AR order (lag regression: use last year's change, 1 = yes)
    sd: int = 1                 # SNARIMAX: seasonal differencing
    sq: int = 0                 # SNARIMAX: seasonal moving-average order
    learning_rate: float = 0.003
    epochs: int = 3             # lag regression: passes over the training weeks
    interval: float = 0.8       # width of the confidence band (0.8 = 10 % and 90 % quantiles)


def build_exogenous(weather: pd.DataFrame, rates: pd.DataFrame | None, names: list[str]) -> pd.DataFrame:
    """Weekly exogenous variables (columns = the chosen names) on the weather's weekly index."""
    available = weather.assign(snowpack=weather["snowfall"].rolling(SNOWPACK_WEEKS, min_periods=1).sum())
    if rates is not None:
        # Business-day rates as weekly means; reindex fills weeks without a rate (e.g. Christmas).
        available["eur_nok"] = rates["EUR"].reindex(available.index).ffill().bfill()
    return available[[name for name in names if name in available]]


def time_of_year(week: pd.Timestamp) -> dict[str, float]:
    """Sine and cosine of the time of year (1, 2 and 3 cycles per year), so the model knows the season."""
    angle = 2 * np.pi * week.dayofyear / 365.25
    terms = {}
    for k in (1, 2, 3):
        terms[f"sin{k}"], terms[f"cos{k}"] = np.sin(k * angle), np.cos(k * angle)
    return terms


def future_exogenous(exog: pd.DataFrame, train_end: pd.Timestamp, horizon: int) -> pd.DataFrame:
    """Exogenous values for the forecast weeks: the weekly climatology for weather, the last value for money.

    The climatology is the mean of the same ISO week in the training years, so a forecast for April uses
    a typical April. Only data up to train_end is used, so the forecast never sees the future.
    """
    past = exog.loc[:train_end]
    weeks = pd.date_range(train_end + pd.Timedelta(weeks=1), periods=horizon, freq="W-SUN")
    climatology = past.groupby(past.index.isocalendar().week.to_numpy()).mean()
    # Week 53 only exists in some years; if it is missing, the neighbouring week fills the gap.
    future = climatology.reindex(weeks.isocalendar().week.to_numpy()).ffill().bfill()
    future.index = weeks
    for column in [c for c in past.columns if c.startswith("eur")]:
        future[column] = past[column].iloc[-1]  # an exchange rate has no season: keep the last value
    return future


def lag_features(levels: np.ndarray, week: pd.Timestamp, exog_row: dict, settings: Settings) -> dict:
    """Features for predicting the change from the last known week to `week` (lag regression)."""
    changes = np.diff(levels[-(WEEKS_PER_YEAR + 2):])  # weekly changes, the newest last
    features = {"level": levels[-1]}                    # high fill levels rise more slowly
    for lag in range(1, settings.p + 1):
        features[f"change_lag{lag}"] = changes[-lag]
    if settings.sp:
        features["change_last_year"] = changes[-WEEKS_PER_YEAR]  # same week one year earlier
    return features | time_of_year(week) | exog_row


def regression(settings: Settings, loss: optim.losses.RegressionLoss) -> preprocessing.StandardScaler:
    """A River pipeline: standardise the features, then an online linear regression trained with SGD."""
    return preprocessing.StandardScaler() | linear_model.LinearRegression(
        optimizer=optim.SGD(settings.learning_rate), intercept_lr=settings.learning_rate, loss=loss)


def exog_rows(exog: pd.DataFrame | None, weeks: pd.DatetimeIndex) -> list[dict]:
    """One {name: value} dictionary per week (River takes features as dictionaries)."""
    if exog is None or exog.empty:
        return [{} for _ in weeks]
    return exog.reindex(weeks).ffill().bfill().to_dict("records")


def forecast_lag_regression(fill: pd.Series, exog: pd.DataFrame | None, train: pd.DatetimeIndex,
                            future: pd.DatetimeIndex, future_exog: list[dict], settings: Settings,
                            loss: optim.losses.RegressionLoss) -> np.ndarray:
    """Train the lag regression on the training weeks and forecast the future weeks dynamically."""
    model = regression(settings, loss)
    values = fill.loc[:train[-1]].to_numpy()
    start = len(values) - len(train)  # position of the first training week
    rows = exog_rows(exog, train)
    for _ in range(settings.epochs):
        for i, (week, row) in enumerate(zip(train, rows)):
            known = values[: start + i]  # everything known before this week (a view, not a copy)
            model.learn_one(lag_features(known, week, row, settings), values[start + i] - known[-1])
    levels = values.copy()
    for week, row in zip(future, future_exog):
        change = model.predict_one(lag_features(levels, week, row, settings))
        # The forecast becomes the newest "known" level: this is what makes the forecast dynamic.
        levels = np.append(levels, np.clip(levels[-1] + change, 0, 100))  # a fill level stays in 0–100 %
    return levels[len(values):]


def forecast_snarimax(fill: pd.Series, exog: pd.DataFrame | None, train: pd.DatetimeIndex,
                      future_exog: list[dict], settings: Settings,
                      loss: optim.losses.RegressionLoss) -> np.ndarray:
    """Train River's SNARIMAX on the training weeks and forecast the future weeks dynamically."""
    model = time_series.SNARIMAX(p=settings.p, d=settings.d, q=settings.q, m=WEEKS_PER_YEAR,
                                 sp=settings.sp, sd=settings.sd, sq=settings.sq,
                                 regressor=regression(settings, loss))
    for value, row in zip(fill.loc[train], exog_rows(exog, train)):
        model.learn_one(value, x=row)
    return np.clip(model.forecast(horizon=len(future_exog), xs=future_exog), 0, 100)


def forecast_fill(fill: pd.Series, exog: pd.DataFrame | None, train_end: pd.Timestamp,
                  settings: Settings = Settings(), with_band: bool = True,
                  train_start: pd.Timestamp | None = None) -> pd.DataFrame:
    """Forecast the fill level (percent) for settings.horizon weeks after train_end.

    fill: weekly fill level in percent (index = Sunday of each week), at least WARM_UP weeks before
    the training period. exog: weekly exogenous variables on the same index, or None.
    The training period is train_start–train_end; without train_start it is settings.history_years long.
    Returns one row per future week with the forecast and, if with_band, the lower and upper quantiles.
    """
    fill = fill.asfreq("W-SUN").interpolate()  # a missing week would break the weekly lags
    end = fill.index.get_loc(train_end)
    if train_start is None:
        first = end + 1 - WEEKS_PER_YEAR * settings.history_years
    else:
        first = fill.index.get_loc(train_start)
    first = max(WARM_UP, first)  # the first weeks are only used as lags
    if exog is not None and not exog.empty and exog.index[0] > fill.index[first]:
        # Training cannot start before the exogenous data do (the weekly weather starts in 2016).
        first = fill.index.searchsorted(exog.index[0])
    train = fill.index[first: end + 1]
    future_frame = future_exogenous(exog, train_end, settings.horizon) if exog is not None and not exog.empty \
        else pd.DataFrame(index=pd.date_range(train_end + pd.Timedelta(weeks=1), periods=settings.horizon,
                                              freq="W-SUN"))
    future_exog = exog_rows(future_frame, future_frame.index)  # [{}, {}, ...] without exogenous data

    def run(loss: optim.losses.RegressionLoss) -> np.ndarray:
        """One model trained with the given loss."""
        if settings.model == "SNARIMAX":
            return forecast_snarimax(fill, exog, train, future_exog, settings, loss)
        return forecast_lag_regression(fill, exog, train, future_frame.index, future_exog, settings, loss)

    result = pd.DataFrame({"forecast": run(optim.losses.Squared())}, index=future_frame.index)
    if with_band:
        tail = (1 - settings.interval) / 2  # 0.8 -> the 10 % and 90 % quantiles
        result["lower"] = run(optim.losses.Quantile(tail))
        result["upper"] = run(optim.losses.Quantile(1 - tail))
        # Separate models can cross; sort so that lower <= forecast <= upper in every week.
        result[["lower", "forecast", "upper"]] = np.sort(result[["lower", "forecast", "upper"]], axis=1)
    return result


def mean_absolute_error(forecast: pd.DataFrame, fill: pd.Series) -> float | None:
    """Mean absolute error in percentage points for the forecast weeks that have been observed."""
    actual = fill.reindex(forecast.index).dropna()
    if actual.empty:
        return None
    return float((forecast.loc[actual.index, "forecast"] - actual).abs().mean())


def with_settings(settings: Settings, **changes: object) -> Settings:
    """A copy of the settings with some values changed (used by the tests in the notebook)."""
    return replace(settings, **changes)
