"""Forecast – Reservoir forecast: dynamic forecasts of the weekly fill level with River models.

- Area and time period are shared with the Map and Weather vs. reservoir pages: the model trains on the
  chosen period and forecasts the weeks after its last week. If the period ends in the past, the
  forecast can be compared with what really happened (a backtest).
- Model, model parameters, horizon and exogenous variables (weather, exchange rate) are chosen here.
- The result is drawn as a Plotly animation: press Play to see the forecast grow week by week.
The model code is in src/utils/forecast.py; the notebook (section 7) tests it and chose the defaults.
"""

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from src.utils.controls import area_controls, period_slider
from src.utils.currency import load_weekly_rates
from src.utils.forecast import (DEFAULT_EXOGENOUS, EXOGENOUS, MODELS, Settings, build_exogenous,
                                forecast_fill, mean_absolute_error)
from src.utils.nve_api import load_areas, load_data, nve_or_stop
from src.utils.ui import ACCENT, HIGHLIGHT, NAVY, page_header, show_plot
from src.utils.weather_history import area_weather_or_stop, weekly_weather_or_stop


DEFAULTS = Settings()
SHOWN_HISTORY_WEEKS = 104  # weeks of training data drawn before the forecast


def fill_series(frame: pd.DataFrame, area_type: str, number: int) -> pd.Series:
    """One area's weekly fill level in percent, indexed by the Sunday that ends each week."""
    rows = frame.loc[(frame["area_type"] == area_type) & (frame["area_number"] == number)]
    return rows.set_index("date")["fill_level"].sort_index() * 100


def choose_settings() -> Settings:
    """Model settings: model type, horizon, orders, learning rate, epochs and band width."""
    model = st.radio("Model", MODELS, horizontal=True,
                     help="Lag regression predicts the weekly change from lags, season and the exogenous "
                          "variables. SNARIMAX is River's seasonal ARIMA with exogenous variables.")
    left, middle, right = st.columns(3)
    horizon = left.slider("Forecast horizon (weeks)", 4, 52, DEFAULTS.horizon)
    p = middle.slider("p: recent weeks (AR order)", 0, 6, DEFAULTS.p)
    sp = right.slider("sp: seasonal AR order (last year)", 0, 2, DEFAULTS.sp)
    learning_rate = left.select_slider("Learning rate (SGD)", [0.0003, 0.001, 0.003, 0.01, 0.03],
                                       value=DEFAULTS.learning_rate)
    interval = middle.select_slider("Confidence band", [0.5, 0.8, 0.9], value=DEFAULTS.interval,
                                    format_func=lambda share: f"{share:.0%}")
    if model == "SNARIMAX":
        d = right.slider("d: differencing", 0, 2, 0)
        q = left.slider("q: MA order", 0, 3, 0)
        sd = middle.slider("sd: seasonal differencing", 0, 1, 1)
        sq = right.slider("sq: seasonal MA order", 0, 2, 0)
        return Settings(model=model, horizon=horizon, p=p, d=d, q=q, sp=sp, sd=sd, sq=sq,
                        learning_rate=learning_rate, interval=interval)
    epochs = right.slider("Epochs (passes over the training weeks)", 1, 10, DEFAULTS.epochs)
    return Settings(model=model, horizon=horizon, p=p, sp=sp, learning_rate=learning_rate,
                    epochs=epochs, interval=interval)


@st.cache_data(show_spinner="Training the River models and forecasting…", max_entries=50)
def run_forecast(fill: pd.Series, exog: pd.DataFrame | None, train_start: pd.Timestamp,
                 train_end: pd.Timestamp, settings: Settings, observed_future: bool) -> pd.DataFrame:
    """Cached forecast: the same area, period, variables and settings are only trained once."""
    return forecast_fill(fill, exog, train_end, settings, with_band=True, train_start=train_start,
                         observed_future=observed_future)


def animated_figure(history: pd.Series, actual: pd.Series, forecast: pd.DataFrame, title: str) -> go.Figure:
    """Plotly animation: the forecast and its band grow one week per frame after the training data."""
    def forecast_traces(weeks: int) -> list[go.Scatter]:
        """The band and the forecast line for the first `weeks` forecast weeks."""
        part = forecast.iloc[:weeks]
        # Joined to the last training week, so the forecast line starts where the data end.
        x = [history.index[-1], *part.index]
        return [
            go.Scatter(x=[*x, *x[::-1]], y=[history.iloc[-1], *part["upper"], *part["lower"][::-1],
                                           history.iloc[-1]],
                       mode="lines", fill="toself", fillcolor="rgba(179,90,18,0.15)",
                       line={"width": 0, "color": "rgba(179,90,18,0)"}, name="Confidence band", hoverinfo="skip"),
            go.Scatter(x=x, y=[history.iloc[-1], *part["forecast"]], mode="lines+markers",
                       line={"color": HIGHLIGHT, "width": 2.2}, marker={"size": 4}, name="Forecast",
                       hovertemplate="%{x|%d %b %Y}<br>%{y:.1f} %<extra>Forecast</extra>"),
        ]
    static = [
        go.Scatter(x=history.index, y=history, mode="lines", line={"color": ACCENT, "width": 1.6},
                   name="Training data", hovertemplate="%{x|%d %b %Y}<br>%{y:.1f} %<extra></extra>"),
        go.Scatter(x=actual.index, y=actual, mode="lines", line={"color": NAVY, "width": 1.4, "dash": "dot"},
                   name="Observed (not used)", hovertemplate="%{x|%d %b %Y}<br>%{y:.1f} %<extra></extra>"),
    ]
    frames = [go.Frame(data=forecast_traces(k), name=str(k), traces=[2, 3]) for k in range(1, len(forecast) + 1)]
    figure = go.Figure(data=static + forecast_traces(len(forecast)), frames=frames)
    play = {"label": "▶ Play", "method": "animate",
            "args": [None, {"frame": {"duration": 120, "redraw": True}, "fromcurrent": False,
                            "transition": {"duration": 0}}]}
    figure.update_layout(
        title=title, height=520, yaxis_title="Fill level (%)", yaxis_range=[0, 100],
        # A fixed time axis, so the plot does not jump while the forecast grows.
        xaxis_range=[history.index[0], forecast.index[-1] + pd.Timedelta(weeks=2)],
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
        updatemenus=[{"type": "buttons", "buttons": [play], "x": 0, "y": -0.12, "xanchor": "left"}],
        sliders=[{"steps": [{"label": f"{week:%d %b}", "method": "animate",
                             "args": [[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]}
                            for k, week in enumerate(forecast.index, start=1)],
                  "active": len(forecast) - 1,  # start by showing the whole forecast
                  "x": 0.1, "len": 0.9, "y": -0.08, "currentvalue": {"prefix": "Forecast to "}}],
    )
    return figure


def show_statistics(forecast: pd.DataFrame, fill: pd.Series, train_weeks: int) -> None:
    """Key numbers: training length, forecast at the horizon and the error if the weeks are observed."""
    error = mean_absolute_error(forecast, fill)
    last = forecast.iloc[-1]
    cards = [("Training weeks", f"{train_weeks:,}"),
             (f"Forecast {forecast.index[-1]:%d %b %Y}", f"{last['forecast']:.1f} %"),
             ("Band at the horizon", f"{last['lower']:.0f}–{last['upper']:.0f} %"),
             ("Mean absolute error", f"{error:.1f} pp" if error is not None else "not observed yet")]
    for column, (label, value) in zip(st.columns(4), cards):
        column.metric(label, value)


def render_page() -> None:
    """Draw the page: shared area and period, model settings, exogenous variables and the animation."""
    page_header("Forecast", "Reservoir forecast",
                "Forecast the coming months' fill level with online machine learning (River).")
    frame = nve_or_stop(load_data)
    areas = nve_or_stop(load_areas)
    weather = weekly_weather_or_stop()
    with st.container(border=True):
        area_type, number, name = area_controls(frame, areas)
        weeks = [pd.Timestamp(week) for week in sorted(frame["date"].unique())]
        train_start, train_end = period_slider(weeks, label="Training period (the forecast starts after it)")
        st.caption("The area and the period are shared with the Map and Weather vs. reservoir pages.")
    with st.container(border=True):
        settings = choose_settings()
        names = st.multiselect("Exogenous variables", list(EXOGENOUS), default=DEFAULT_EXOGENOUS,
                               format_func=EXOGENOUS.get,
                               help="Future weather is unknown: the forecast uses the mean of the same week "
                                    "in the training years. The exchange rate keeps its last value.")
        # Only in a backtest (period ending in the past) can the observed weather of the forecast weeks be used.
        observed_future = st.toggle(
            "Backtest with the observed weather (a perfect weather forecast)", value=False,
            disabled=train_end + pd.Timedelta(weeks=settings.horizon) > weeks[-1] or not names,
            help="For a training period that ends in the past: use the weather that really came instead of "
                 "the climatology. Shows how much better the forecast would be with a perfect weather forecast.")

    fill = fill_series(frame, area_type, number)
    area_weekly = area_weather_or_stop(weather, area_type, number, name)
    if names and train_start < area_weekly.index[0]:
        st.info(f"The weekly weather starts {area_weekly.index[0]:%d %b %Y}; training starts there.")
        train_start = area_weekly.index[0]
    rates = None
    if "eur_nok" in names:
        try:
            rates = load_weekly_rates(f"{area_weekly.index[0]:%Y-%m-%d}", f"{train_end:%Y-%m-%d}")
        except requests.RequestException as error:  # Norges Bank unreachable: forecast without EUR/NOK
            st.warning(f"Could not download exchange rates from Norges Bank ({type(error).__name__}); "
                       "the forecast runs without EUR/NOK.")
            names = [n for n in names if n != "eur_nok"]
    exog = build_exogenous(area_weekly, rates, names) if names else None

    forecast = run_forecast(fill, exog, train_start, train_end, settings, observed_future and exog is not None)
    history = fill.loc[train_start:train_end].iloc[-SHOWN_HISTORY_WEEKS:]
    actual = fill.loc[forecast.index[0]:forecast.index[-1]]
    show_statistics(forecast, fill, len(fill.loc[train_start:train_end]))
    show_plot(animated_figure(history, actual, forecast,
                              f"{name}: {settings.model}, {settings.horizon} weeks from {train_end:%d %b %Y}"))
    st.caption(f"Shaded: the {settings.interval:.0%} band from two extra models trained with the quantile loss. "
               "Dotted: the observed fill level after the training period, if it exists (not used for training).")
    with st.expander("Forecast values"):
        st.dataframe(forecast.round(1).rename_axis("Week ending"), width="stretch")
        st.download_button("Download the forecast (CSV)", forecast.round(2).to_csv().encode(),
                           file_name=f"forecast_{area_type}{number}_{train_end:%Y%m%d}.csv", mime="text/csv")


render_page()
