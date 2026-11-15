# IND320 · Norwegian power data dashboard

A Streamlit app and Jupyter Notebooks for the IND320 project work (NMBU, autumn 2026).
The app shows Norwegian reservoir levels from NVE, weather from Open-Meteo for the same areas,
exchange rates from Norges Bank and cross-border electricity flows from ENTSO-E, and forecasts the
reservoir fill level with online machine learning (River).

| | |
|---|---|
| 🌐 **Live app** | https://ind320-dashboard-basics-yaksh-git.streamlit.app/ |
| 📓 **Part 4 notebook** | [`notebooks/ind320_part4.ipynb`](notebooks/ind320_part4.ipynb) |
| 🎬 **Part 4 screencast** | [`docs/part_4/screencast_part4.mp4`](docs/part_4/screencast_part4.mp4) |
| 📓 **Part 3 notebook** | [`notebooks/ind320_part3.ipynb`](notebooks/ind320_part3.ipynb) |
| 🎬 **Part 3 screencast** | [`docs/part_3/screencast_part3.mp4`](docs/part_3/screencast_part3.mp4) |
| 📓 **Part 2 notebook** | [`notebooks/ind320_part2.ipynb`](notebooks/ind320_part2.ipynb) |
| 🎬 **Part 2 screencast** | [`docs/part_2/screencast_part2.mp4`](docs/part_2/screencast_part2.mp4) |
| 📁 **Part 1 (archived)** | [`docs/part_1/`](docs/part_1/): notebook and [screencast](docs/part_1/screencast_part1.mp4) |
| 🤖 **Rules for AI agents** | [`AGENTS.md`](AGENTS.md) |

## Data flow

```
NVE Magasinstatistikk API ─────────────────────────────▶ Home, Map, Reservoir data, analysis and forecast pages
NVE map services ─▶ notebook ─▶ data/regions/*.geojson ─▶ Map outlines, random locations
Open-Meteo API (ERA5, hourly) ─────────────────────────▶ Weather outliers (cached requests)
Open-Meteo API (ERA5, daily) ─▶ notebook ─▶ MongoDB ───▶ Map, Weather vs. reservoir, Forecast (weekly weather)
Norges Bank API ───────────────────────────────────────▶ Forecast (EUR/NOK as an exogenous variable)
ENTSO-E API ─▶ Spark ─▶ Cassandra ─▶ Spark ─▶ MongoDB ─▶ Cross-border flows
```

## App pages

The menu is grouped by the type of task (see the sketch in section 2 of the Part 4 notebook). Each
group has its own colour in the page header and on the active menu entry.

| Group | Page | Content | Source |
|---|---|---|---|
| Start | Home | Latest national report, long-term fill level and one card per group | NVE API |
| Start | Map | Areas (GeoJSON) coloured by fill level or weekly weather; a click chooses the area for the other pages | NVE API, MongoDB |
| Explore | Reservoir data | Tabs: Table (one row per area with `LineChartColumn`, one row per API field) and Plot (any field) | NVE API |
| Explore | Fill-level analysis | Tabs: STL decomposition and spectrogram of one area's weekly fill level | NVE API |
| Explore | Weather vs. reservoir | Sliding window correlation with selectable weather property, lag and window | NVE API, MongoDB |
| Anomalies | Weather outliers | Tabs: SPC outliers (DCT high-pass) and LOF anomalies in hourly weather; temperature by default | Open-Meteo API |
| Forecast | Reservoir forecast | River lag regression or SNARIMAX with exogenous variables, dynamic forecast, quantile band, Plotly animation | NVE, MongoDB, Norges Bank |
| Electricity | Cross-border flows | Yearly import/export donut and an interactive chart of hourly or daily-mean flows | MongoDB |
| Info | About | Areas, units and data sources | – |

All charts are interactive Plotly figures with one shared template. The **area** (chosen on any analysis
page or by clicking the map) and the **time period** (Map, Weather vs. reservoir, Forecast) are stored in
`st.session_state`, so they follow the user between pages; year, lag, window and model parameters are
local choices. Every API and database call is cached, shows a spinner and stops the page with a short
message instead of a traceback if the source cannot be reached.

## Repository structure

```
app.py                  entry point and the grouped menu
requirements.txt        packages for the app
src/
  pages/                one file per Streamlit page
  utils/                shared code
    nve_api.py          NVE API requests and field names
    weather_api.py      Open-Meteo (ERA5) hourly requests for one area and year
    weather_history.py  weekly weather for all areas, read from MongoDB
    currency.py         Norges Bank exchange rates (EUR/NOK, USD/NOK)
    analysis.py         SPC (DCT), LOF, STL, spectrogram and sliding window correlation
    forecast.py         River forecasts (lag regression, SNARIMAX, quantile bands)
    flows_db.py         MongoDB client and the cross-border queries
    controls.py         shared interval slider, area choice, period slider and map selection
    ui.py               styling, group colours and the Plotly template
notebooks/
  ind320_part4.ipynb    Part 4: exchange rates, time zones, weekly weather, correlation, forecasting
  ind320_part3.ipynb    Part 3 analysis and documentation
  ind320_part2.ipynb    Part 2 analysis and documentation
  requirements.txt      extra packages for the notebooks (PySpark, Cassandra driver, GeoPandas, Matplotlib)
  export_pdf.py         notebook -> PDF (nbconvert + headless Chrome)
data/regions/           area polygons and 1000 random locations per area (GeoJSON)
docs/part_1/            Part 1 deliverables
docs/part_2/ … part_4/  screencasts and the Part 4 sketch
```

## Run locally

The app needs Python 3.10 or newer. The notebook uses Python 3.12 because of PySpark 3.5.1.

```bash
uv venv --python 3.12 .venv
uv pip install -r notebooks/requirements.txt   # or requirements.txt for the app only
.venv/bin/python -m streamlit run app.py
```

Secrets go in `.streamlit/secrets.toml`, which is ignored by Git:

```toml
[mongo]
uri = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=<app>"
database = "ind320"

[entsoe]
token = "<ENTSO-E security token>"   # only needed by the notebook
```

On Streamlit Community Cloud, paste the `[mongo]` section into *App settings → Secrets*.

### Notebooks

The Part 4 notebook needs the `[mongo]` secret (it stores the weekly weather in MongoDB); its weather
downloads are cached in `data/cache/` and throttled to stay inside Open-Meteo's free limits. The Part 3
notebook needs no secrets or databases. The Part 2 notebook needs Cassandra and Spark:

1. Start Cassandra in Docker: `docker run --name my_cassandra -p 9042:9042 -d cassandra:latest`
   (later: `docker start my_cassandra`).
2. Install Java 17 (PySpark needs it). Spark downloads the Cassandra connector automatically.
3. Run all cells, then export to PDF (HTML via nbconvert, printed with headless Google Chrome;
   the files are written to `output/`, which Git ignores):

   ```bash
   .venv/bin/python notebooks/export_pdf.py
   ```

**Data sources:** [NVE Magasinstatistikk](https://www.nve.no/energi/analyser-og-statistikk/magasinstatistikk/) ·
[NVE Atlas](https://atlas.nve.no) ·
[Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) ·
[Norges Bank](https://app.norges-bank.no/query/#/en/) ·
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
