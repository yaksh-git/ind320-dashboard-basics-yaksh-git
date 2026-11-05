"""Time-series methods for the Part 3 pages: SPC with a DCT filter, LOF, STL and the spectrogram.

The methods are the same as in the Part 3 notebook (notebooks/ind320_part3.ipynb). Each method
has one function that computes the result and one that draws it, so a page can show both the
plot and the statistics behind it.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

from src.utils.ui import ACCENT


HIGHLIGHT = "#B35A12"  # outliers and anomalies (the same orange as "export" on the flows page)
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


def plot_spc(result: pd.DataFrame, label: str, unit: str, title: str) -> Figure:
    """The values with the SPC limits as lines and the outliers in orange (the SATV is not plotted)."""
    outliers = result.loc[result["outlier"]]
    figure, axis = plt.subplots(figsize=(12, 4.6))
    axis.plot(result.index, result["value"], color=ACCENT, linewidth=0.6, label=label)
    axis.plot(result.index, result["upper"], color="#12263A", linewidth=1, label="SPC limits")
    axis.plot(result.index, result["lower"], color="#12263A", linewidth=1)
    axis.scatter(outliers.index, outliers["value"], color=HIGHLIGHT, s=9, zorder=3, label="Outliers")
    axis.set(title=title, xlabel="", ylabel=f"{label} ({unit})")
    axis.legend(loc="upper left", frameon=False, ncol=3)
    return figure


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


def plot_lof(result: pd.DataFrame, label: str, unit: str, title: str) -> Figure:
    """The values over time with the LOF anomalies in orange."""
    anomalies = result.loc[result["anomaly"]]
    figure, axis = plt.subplots(figsize=(12, 4.6))
    axis.plot(result.index, result["value"], color=ACCENT, linewidth=0.6, label=label)
    axis.scatter(anomalies.index, anomalies["value"], color=HIGHLIGHT, s=11, zorder=3, label="LOF anomalies")
    axis.set(title=title, xlabel="", ylabel=f"{label} ({unit})")
    axis.legend(loc="upper left", frameon=False, ncol=2)
    return figure


# ---- Seasonal-Trend decomposition using LOESS ----

def stl_parts(series: pd.Series, seasonal: int, trend: int, robust: bool) -> pd.DataFrame:
    """Observed, trend, seasonal and remainder columns of an STL fit with a 52-week period."""
    result = STL(series.interpolate(), period=WEEKS_PER_YEAR, seasonal=seasonal, trend=trend,
                 robust=robust).fit()
    return pd.DataFrame({"Observed": result.observed, "Trend": result.trend,
                         "Seasonal": result.seasonal, "Remainder": result.resid})


def plot_stl(parts: pd.DataFrame, title: str) -> Figure:
    """Four panels that share the time axis: observed, trend, seasonal and remainder (fill fraction)."""
    figure, axes = plt.subplots(4, 1, figsize=(12, 8.5), sharex=True)
    for axis, name in zip(axes, parts.columns):
        axis.plot(parts.index, parts[name], color=ACCENT, linewidth=0.9)
        axis.set(ylabel=name)
    axes[-1].axhline(0, color="#12263A", linewidth=0.6)
    axes[0].set_title(title)
    figure.supylabel("Fill level (fraction full)", color="#526477")
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


def plot_spectrogram(years: np.ndarray, freqs: np.ndarray, power_db: np.ndarray, title: str) -> Figure:
    """Spectrogram as a colour map: time on x, frequency (0–6 cycles per year) on y, power as colour."""
    figure, axis = plt.subplots(figsize=(12, 4.8))
    mesh = axis.pcolormesh(years, freqs, power_db, shading="gouraud", cmap="viridis")
    figure.colorbar(mesh, ax=axis, label="Power (dB)")
    # Above 6 cycles per year there is only noise; the yearly cycle and its harmonics are below.
    axis.set(title=title, xlabel="Year", ylabel="Frequency (cycles per year)", ylim=(0, 6))
    axis.grid(False)
    return figure
