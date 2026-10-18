# IND320 · Norwegian power data dashboard

A Streamlit app and Jupyter Notebooks for the IND320 project work (NMBU, autumn 2026).
The app shows Norwegian reservoir levels from NVE and cross-border electricity flows from ENTSO-E.

| | |
|---|---|
| 🌐 **Live app** | https://ind320-dashboard-basics-yaksh-git.streamlit.app/ |
| 📓 **Part 2 notebook** | [`notebooks/ind320_part2.ipynb`](notebooks/ind320_part2.ipynb) |
| 📁 **Part 1 (archived)** | [`docs/part_1/`](docs/part_1/): notebook and [screencast](docs/part_1/screencast_part1.mp4) |
| 🤖 **Rules for AI agents** | [`AGENTS.md`](AGENTS.md) |

## Data flow

```
NVE Magasinstatistikk API ─────────────────────────────▶ app pages 1–3 (cached requests)
ENTSO-E API ─▶ Spark ─▶ Cassandra ─▶ Spark ─▶ MongoDB ─▶ app page 4
```

## App pages

| # | Page | Content | Source |
|---|---|---|---|
| 1 | Home | Latest national report and long-term fill level | NVE API |
| 2 | Data table | One row per area with a fill-level line (`LineChartColumn`), plus one row per API field | NVE API |
| 3 | Data plot | Any field over time, one line per area | NVE API |
| 4 | Cross-border flows | Yearly import/export pie (connection + year) and hourly flows for any set of months | MongoDB |
| 5 | About | Areas, units and data sources (page 4 in Part 1) | – |

Pages 2 and 3 share two controls: the **download interval** (month slider) and the **type of area**
(`st.radio`: EL, NO, VASS). The NVE API has no date parameters, so the app downloads the full history
once (cached) and keeps the chosen interval.

## Repository structure

```
app.py                  entry point and page navigation
requirements.txt        packages for the app
src/
  pages/                one file per Streamlit page
  utils/                shared code
    nve_api.py          NVE API requests and field names
    flows_db.py         MongoDB queries for the cross-border page
    controls.py         shared interval slider and area-type radio (pages 2 and 3)
    ui.py               shared styling and chart helpers
notebooks/
  ind320_part2.ipynb    Part 2 analysis and documentation
  requirements.txt      extra packages for the notebook (PySpark, Cassandra driver)
docs/part_1/            Part 1 deliverables
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

### Notebook

1. Start Cassandra in Docker: `docker run --name my_cassandra -p 9042:9042 -d cassandra:latest`
   (later: `docker start my_cassandra`).
2. Install Java 17 (PySpark needs it). Spark downloads the Cassandra connector automatically.
3. Run all cells, then export to PDF.

**Data sources:** [NVE Magasinstatistikk](https://www.nve.no/energi/analyser-og-statistikk/magasinstatistikk/) ·
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
