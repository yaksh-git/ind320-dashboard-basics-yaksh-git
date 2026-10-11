# AGENTS.md

Rules for AI coding agents (Codex, Claude Code, Copilot, …) working in this repository.
Keep this file short and up to date when the structure changes.

## Project

IND320 project work (NMBU): a Streamlit app and a Jupyter Notebook that grow over four parts.
The student submits the work and must be able to explain every part of it, so prefer clear,
commented code over clever code, and explain changes in plain language.

## Structure

| Path | Content |
|---|---|
| `app.py` | Entry point and page navigation. Page order follows the assignment: 4 Reservoir areas, 5 About, 6 Cross-border flows |
| `pages/` | One file per Streamlit page |
| `dashboard/` | Shared app code: `nve_api.py` (NVE API), `flows_db.py` (MongoDB queries), `ui.py` (styling) |
| `notebooks/` | `ind320_part2.ipynb`, the analysis and documentation deliverable |
| `docs/part1/` | Archived Part 1 (notebook, generator, screencast). Do not change |
| `data/cache/` | Downloaded API data, ignored by Git, re-created by the notebook |
| `requirements.txt` | App packages (installed by Streamlit Community Cloud) |
| `requirements-notebook.txt` | Adds PySpark, the Cassandra driver and Jupyter tools for the notebook |

## Commands

```bash
uv venv --python 3.12 .venv && uv pip install -r requirements-notebook.txt
.venv/bin/python -m streamlit run app.py
docker start my_cassandra            # first time: docker run --name my_cassandra -p 9042:9042 -d cassandra:latest
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/ind320_part2.ipynb
```

## Rules

- **Secrets** live only in `.streamlit/secrets.toml` (Git-ignored) and in the Streamlit Cloud secrets.
  Never commit, print or ask for passwords, tokens or connection strings. Error messages must not
  include request URLs that contain the ENTSO-E token.
- **Git:** work on the branch for the current part (Part 2: `codex/ind320-part2`). Merge into `main`
  only when the student asks. Do not commit `notes/`.
- **Language:** code, comments, notebook and app text in English. Talk to the student in Norwegian.
- **Comments:** every notebook cell and app function needs enough comments to be understood and
  reproduced by someone who inherits the project. Explain the reasons, units and time zones.
- **Versions** (course book): Python 3.12, PySpark 3.5.1 with `spark-cassandra-connector_2.12:3.5.1`,
  Java 17, Cassandra in Docker.
- **Time columns:** NVE `dato_Id` is the Sunday that ends the ISO week. `neste_Publiseringsdato` year 0001
  means no date. ENTSO-E times are UTC; year and month are derived in `Europe/Oslo`. Always pass an
  explicit date format when parsing.
- **Units:** ENTSO-E physical flows are MW per direction (not netted). Convert to MWh with the
  resolution (PT15M/PT60M) before summing. Never put different units on one y-axis.
- **Plots:** Seaborn/Matplotlib with `dashboard.ui.chart_style()`. Draw one line per area or link, never
  a single line that mixes areas.
- **Ownership:** do not write the work log or the AI-usage statement as if you were the student. Give
  facts and drafts that the student rewrites in their own words.
- **Before submission:** re-read the current assignment text on Canvas (it may be revised), run all
  notebook cells before the PDF export, and test every page of the deployed app.

## Sources

- Course book: https://github.com/khliland/IND320 (`D2Dbook/2_Data_sources/2_Databases`, `7_Appendix/Installation.ipynb`)
- NVE API: https://biapi.nve.no/magasinstatistikk/swagger/index.html
- ENTSO-E API: https://documenter.getpostman.com/view/7009892/2s93JtP3F6
