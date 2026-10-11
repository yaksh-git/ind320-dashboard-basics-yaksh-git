# IND320 Dashboard

Streamlit app and Jupyter Notebooks for the IND320 project work.

- **Live app:** https://ind320-dashboard-basics-yaksh-git.streamlit.app/
- **Part 2 notebook:** [`notebooks/ind320_part2.ipynb`](notebooks/ind320_part2.ipynb): NVE API, ENTSO-E, Cassandra/Spark and MongoDB
- **Part 1 (archived):** [`docs/part1/`](docs/part1/), with the notebook, its generator and the screencast
- **Rules for AI agents:** [`AGENTS.md`](AGENTS.md) (Claude Code reads it through `CLAUDE.md`)

## Data flow (Part 2)

```
NVE Magasinstatistikk API ─────────────────────────────▶ app pages 1–4 (cached requests)
ENTSO-E API ─▶ Spark ─▶ Cassandra ─▶ Spark ─▶ MongoDB ─▶ app page 6
```

| Page | Content | Source |
|---|---|---|
| 1 Home | Latest national report and long-term fill level | NVE API |
| 2 Data table | One row per API field with first-month sparklines | NVE API |
| 3 Data plot | Any field over a chosen month range | NVE API |
| 4 Reservoir areas | Interval slider + EL/NO/VASS radio, fill level per area | NVE API |
| 5 About | Areas, units and data sources (page 4 in Part 1) | – |
| 6 Cross-border flows | Yearly pie and monthly hourly flows per connection | MongoDB |

## Folder structure

```
app.py                  entry point and page navigation
pages/                  one file per Streamlit page
dashboard/              shared app code
  nve_api.py            NVE API requests and field names
  flows_db.py           MongoDB queries for the cross-border page
  ui.py                 shared styling
notebooks/              Part 2 notebook (analysis and documentation)
docs/part1/             archived Part 1 deliverables
data/cache/             downloaded API data (ignored by Git)
```

## Run the app locally

The app needs Python 3.10 or newer. The notebook uses Python 3.12 because of PySpark 3.5.1.

```bash
uv venv --python 3.12 .venv
uv pip install -r requirements-notebook.txt   # or requirements.txt for the app only
.venv/bin/python -m streamlit run app.py
```

Secrets go in `.streamlit/secrets.toml`, which is ignored by Git:

```toml
[mongo]
uri = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
database = "ind320"

[entsoe]
token = "<ENTSO-E security token>"   # only needed by the notebook
```

On Streamlit Community Cloud, paste the `[mongo]` section into *App settings → Secrets*.

## Run the notebook

1. Start Cassandra in Docker: `docker run --name my_cassandra -p 9042:9042 -d cassandra:latest`
   (later: `docker start my_cassandra`).
2. Install Java 17 (PySpark needs it). Spark downloads the Cassandra connector automatically.
3. Run all cells, then export to PDF.

Data sources: [NVE Magasinstatistikk](https://www.nve.no/energi/analyser-og-statistikk/magasinstatistikk/),
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).
