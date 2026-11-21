"""Time-series methods for the Part 3 pages: SPC with a DCT filter, LOF, STL and the spectrogram.

The methods are the same as in the Part 3 notebook (notebooks/ind320_part3.ipynb). Each method
has one function that computes the result and one that draws it, so a page can show both the
plot and the statistics behind it. Part 4: the drawing functions return interactive Plotly figures.
"""

import numpy as np
import pandas as pd
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.ui import ACCENT, HIGHLIGHT, NAVY


WEEKS_PER_YEAR = 52    # period of the weekly fill level and sampling frequency of the spectrogram
MAD_TO_SD = 1.4826     # MAD × 1.4826 equals the standard deviation for normally distributed data


# ---- Outliers: Statistical Process Control on DCT-filtered data ----

def spc_outliers(series: pd.Series, cutoff_per_year: float, n_sd: float) -> tuple[pd.DataFrame, float]:
    """SPC limits and an outlier flag for every value; also returns the robust standard deviation."""
    values = series.to_numpy()
    years = (series.index[-1] - series.index[0]).total_seconds() / (365.25 * 24 * 3600)
    # DCT coefficient k is k/2 cycles over the whole series, so the cut-off maps to k = 2 * cutoff * years.
    k = int(round(2 * cutoff_per_year * years))
    low = dct(values, norm="ortho")
    low[k:] = 0                                      # keep only the slow (seasonal) part ...
    seasonal = idct(low, norm="ortho")
    satv = values - seasonal                         # ... the rest is the SATV (high-pass)
    centre = np.median(satv)
    sd = MAD_TO_SD * np.median(np.abs(satv - centre))  # robust: not pulled by the outliers themselves
    result = pd.DataFrame({"value": values, "satv": satv,
                           "upper": seasonal + centre + n_sd * sd,
                           "lower": seasonal + centre - n_sd * sd}, index=series.index)
    result["outlier"] = np.abs(satv - centre) > n_sd * sd
    return result, sd


def legend_on_top(figure: go.Figure) -> go.Figure:
    """Put the legend in one row above the plot, so it never covers the data."""
    return figure.update_layout(legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0})


def plot_spc(result: pd.DataFrame, label: str, unit: str, title: str) -> go.Figure:
    """The values with the SPC limits as lines and the outliers in orange (the SATV is not plotted)."""
    outliers = result.loc[result["outlier"]]
    figure = go.Figure()
    # Scattergl draws the 8,784 hourly points with WebGL, which keeps zooming smooth.
    figure.add_trace(go.Scattergl(x=result.index, y=result["value"], name=label, mode="lines",
                                  line={"color": ACCENT, "width": 0.8}))
    figure.add_trace(go.Scattergl(x=result.index, y=result["upper"], name="SPC limits", mode="lines",
                                  line={"color": NAVY, "width": 1}, legendgroup="limits"))
    figure.add_trace(go.Scattergl(x=result.index, y=result["lower"], name="SPC limits", mode="lines",
                                  line={"color": NAVY, "width": 1}, legendgroup="limits", showlegend=False))
    figure.add_trace(go.Scattergl(x=outliers.index, y=outliers["value"], name="Outliers", mode="markers",
                                  marker={"color": HIGHLIGHT, "size": 5}))
    figure.update_layout(title=title, yaxis_title=f"{label} ({unit})", hovermode="x unified")
    return legend_on_top(figure)


# ---- Anomalies: Local Outlier Factor ----

def lof_anomalies(series: pd.Series, proportion: float, n_neighbors: int = 48) -> pd.DataFrame:
    """LOF score and anomaly flag for every value; time and value are the two features."""
    days = (series.index - series.index[0]).total_seconds().to_numpy() / (24 * 3600)
    features = np.column_stack([days, series.to_numpy()])
    spread = features.std(axis=0)
    spread[spread == 0] = 1                          # a constant column (e.g. no snow) cannot be scaled
    features = (features - features.mean(axis=0)) / spread  # same scale for time and value
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=proportion)
    is_anomaly = lof.fit_predict(features) == -1     # -1 = anomaly, 1 = normal
    return pd.DataFrame({"value": series, "lof_score": -lof.negative_outlier_factor_,
                         "anomaly": is_anomaly}, index=series.index)


def plot_lof(result: pd.DataFrame, label: str, unit: str, title: str) -> go.Figure:
    """The values over time with the LOF anomalies in orange."""
    anomalies = result.loc[result["anomaly"]]
    figure = go.Figure()
    figure.add_trace(go.Scattergl(x=result.index, y=result["value"], name=label, mode="lines",
                                  line={"color": ACCENT, "width": 0.8}))
    figure.add_trace(go.Scattergl(x=anomalies.index, y=anomalies["value"], name="LOF anomalies",
                                  mode="markers", marker={"color": HIGHLIGHT, "size": 6},
                                  customdata=anomalies["lof_score"],
                                  hovertemplate="%{x}<br>%{y:.2f}<br>LOF score %{customdata:.2f}<extra></extra>"))
    figure.update_layout(title=title, yaxis_title=f"{label} ({unit})")
    return legend_on_top(figure)


# ---- Seasonal-Trend decomposition using LOESS ----

def stl_parts(series: pd.Series, seasonal: int, trend: int, robust: bool) -> pd.DataFrame:
    """Observed, trend, seasonal and remainder columns of an STL fit with a 52-week period."""
    result = STL(series.interpolate(), period=WEEKS_PER_YEAR, seasonal=seasonal, trend=trend,
                 robust=robust).fit()
    return pd.DataFrame({"Observed": result.observed, "Trend": result.trend,
                         "Seasonal": result.seasonal, "Remainder": result.resid})


def plot_stl(parts: pd.DataFrame, title: str) -> go.Figure:
    """Four panels that share the time axis: observed, trend, seasonal and remainder (fill fraction)."""
    figure = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04)
    for row, name in enumerate(parts.columns, start=1):
        figure.add_trace(go.Scatter(x=parts.index, y=parts[name], name=name, mode="lines",
                                    line={"color": ACCENT, "width": 1.2}), row=row, col=1)
        # Each panel has its own y-axis title; all four are in the same unit (fraction full).
        figure.update_yaxes(title_text=f"{name}<br>(fraction)", row=row, col=1)
    figure.add_hline(y=0, line={"color": NAVY, "width": 0.8}, row=4, col=1)
    figure.update_layout(title=title, showlegend=False, height=720, hovermode="x unified")
    return figure


# ---- Spectrogram ----

def spectrogram_db(series: pd.Series, window_weeks: int,
                   overlap_weeks: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Window centres (decimal years), frequencies (cycles per year) and power (dB) of a weekly series."""
    values = series.interpolate().to_numpy()
    # fs = 52 samples per year, so the frequencies come out in cycles per year.
    freqs, times, power = spectrogram(values - values.mean(), fs=WEEKS_PER_YEAR,
                                      nperseg=window_weeks, noverlap=overlap_weeks)
    start = series.index[0]
    years = start.year + (start.dayofyear - 1) / 365.25 + times
    return years, freqs, 10 * np.log10(power + 1e-12)  # dB; the small constant avoids log(0)


def plot_spectrogram(years: np.ndarray, freqs: np.ndarray, power_db: np.ndarray, title: str) -> go.Figure:
    """Spectrogram as a colour map: time on x, frequency (0–6 cycles per year) on y, power as colour."""
    figure = go.Figure(go.Heatmap(
        x=years, y=freqs, z=power_db, colorscale="Viridis", zsmooth="best",
        colorbar={"title": {"text": "Power (dB)"}},
        hovertemplate="Year %{x:.1f}<br>%{y:.2f} cycles per year<br>%{z:.1f} dB<extra></extra>"))
    # Above 6 cycles per year there is only noise; the yearly cycle and its harmonics are below.
    figure.update_layout(title=title, xaxis_title="Year", yaxis_title="Frequency (cycles per year)",
                         yaxis_range=[0, 6], height=460)
    return figure


# ---- Sliding window correlation (Part 4): weather against the reservoirs ----

def sliding_correlation(weather: pd.Series, reservoir: pd.Series, lag: int, window: int) -> pd.Series:
    """Correlation in a sliding window of `window` weeks between the weather `lag` weeks earlier and
    the reservoir variable now (a positive lag means that the weather comes first)."""
    # shift(lag) moves the weather lag weeks later, so week t is compared with the weather of week t - lag.
    pairs = pd.concat([weather.shift(lag), reservoir], axis=1).dropna()
    # min_periods: the first windows are only computed when at least 80 % of the weeks are there.
    return pairs.iloc[:, 0].rolling(window, min_periods=int(0.8 * window)).corr(pairs.iloc[:, 1])


def lag_correlations(weather: pd.Series, reservoir: pd.Series, max_lag: int = 26) -> pd.Series:
    """Correlation over the whole period for every lag from -max_lag to +max_lag weeks."""
    return pd.Series({lag: weather.shift(lag).corr(reservoir) for lag in range(-max_lag, max_lag + 1)})


def plot_sliding_correlation(weather: pd.Series, reservoir: pd.Series, correlation: pd.Series,
                             weather_label: str, reservoir_label: str, title: str) -> go.Figure:
    """Three panels with a shared time axis: the weather, the reservoir variable and the correlation.

    Each panel has its own y-axis, so the two units are never mixed on one axis.
    """
    figure = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                           row_heights=[0.3, 0.3, 0.4])
    figure.add_trace(go.Scatter(x=weather.index, y=weather, name=weather_label, mode="lines",
                                line={"color": "#0173B2", "width": 1}), row=1, col=1)
    figure.add_trace(go.Scatter(x=reservoir.index, y=reservoir, name=reservoir_label, mode="lines",
                                line={"color": ACCENT, "width": 1}), row=2, col=1)
    figure.add_trace(go.Scatter(x=correlation.index, y=correlation, name="Correlation", mode="lines",
                                line={"color": HIGHLIGHT, "width": 1.6}), row=3, col=1)
    figure.add_hline(y=0, line={"color": NAVY, "width": 0.8}, row=3, col=1)
    figure.update_yaxes(title_text=weather_label, row=1, col=1)
    figure.update_yaxes(title_text=reservoir_label, row=2, col=1)
    figure.update_yaxes(title_text="Correlation", range=[-1, 1], row=3, col=1)
    figure.update_layout(title=title, height=720, showlegend=False, hovermode="x unified")
    return figure


def plot_lag_correlations(correlations: pd.Series, chosen_lag: int) -> go.Figure:
    """Bar chart of the correlation for every lag; the chosen lag is orange."""
    colours = [HIGHLIGHT if lag == chosen_lag else ACCENT for lag in correlations.index]
    figure = go.Figure(go.Bar(x=correlations.index, y=correlations, marker_color=colours,
                              hovertemplate="Lag %{x} weeks<br>Correlation %{y:.2f}<extra></extra>"))
    figure.update_layout(title="Correlation over the whole period for each lag", height=300,
                         xaxis_title="Lag (weeks; positive = weather first)", yaxis_title="Correlation",
                         yaxis_range=[-1, 1])
    return figure
