"""Choose a few representative weather locations from the 1000 random points of an area.

Open-Meteo counts one call per location, so the app and the notebook cannot download all 1000 points.
Many points share an ERA5 grid cell (0.25°) and therefore identical weather, so the mean of the 1000
points is the same as a mean over the area's ERA5 cells, weighted by how many points fall in each cell.
To approximate that mean with only n downloads, the 1000 points are grouped into n compact clusters
(k-means on the map); each cluster is represented by its most common ERA5 cell, weighted by the number
of points in the cluster. Teacher feedback on Part 3 asked for more representative area means; the test
in section 5.4 of the Part 4 notebook shows that 20 weighted cells are much closer to the mean of all
1000 points than 20 random cells (weekly precipitation error 3 % instead of 8 %).

This module has no Streamlit code, so the notebook can import it as well.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


ERA5_GRID = 0.25  # degrees; points in the same grid cell get identical values from Open-Meteo
SEED = 320        # fixed, so the app and the notebook always choose the same cells


def to_grid(points: pd.DataFrame) -> pd.DataFrame:
    """The points moved to the centre of their ERA5 grid cell (columns lon, lat)."""
    return (points[["lon", "lat"]] / ERA5_GRID).round() * ERA5_GRID


def representative_cells(points: pd.DataFrame, n: int, seed: int = SEED) -> pd.DataFrame:
    """n ERA5 cells that represent the points, with weights = share of the points (columns lat, lon, weight)."""
    # Scale the longitude so that one unit is about as long east-west as north-south at this latitude.
    xy = np.column_stack([points["lon"] * np.cos(np.radians(points["lat"].mean())), points["lat"]])
    labels = KMeans(n_clusters=n, n_init=4, random_state=seed).fit_predict(xy)
    cells = to_grid(points).assign(cluster=labels)
    chosen = []
    for _, cluster in cells.groupby("cluster"):
        lon, lat = cluster.groupby(["lon", "lat"]).size().idxmax()  # the cell with most points in the cluster
        chosen.append({"lat": lat, "lon": lon, "weight": len(cluster)})
    # Two clusters can pick the same cell; download it once and add the weights.
    result = pd.DataFrame(chosen).groupby(["lat", "lon"], as_index=False)["weight"].sum()
    result["weight"] = result["weight"] / result["weight"].sum()
    return result


def weighted_area_mean(per_location: pd.DataFrame, weights: pd.Series, by: str, columns: list[str]) -> pd.DataFrame:
    """Weighted mean over the locations for each value of `by` (per_location has a 'location' column)."""
    weighted = per_location[columns].mul(per_location["location"].map(weights), axis=0)
    return weighted.groupby(per_location[by]).sum()  # the weights sum to 1
