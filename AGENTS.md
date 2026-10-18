# AGENTS.md

Rules for AI coding agents (Codex, Claude Code, Copilot, …) working in this repository.
Claude Code reads this file through `.claude/CLAUDE.md`. Keep it short and update it when the
structure changes.

## Project

IND320 project work (NMBU): a Streamlit app and a Jupyter Notebook that grow over four parts.
The student submits the work and must be able to **explain every line**. Prefer clear,
commented code over clever code, and explain changes in plain language.

## Repository structure

```
app.py                  entry point: page navigation only
requirements.txt        app packages (installed by Streamlit Community Cloud)
src/pages/              one file per Streamlit page
src/utils/              shared code: nve_api.py (NVE API), flows_db.py (MongoDB), controls.py
                        (interval slider + area-type radio for pages 2–3), ui.py (styling)
notebooks/              the part's notebook + requirements.txt with the notebook-only packages
docs/part_<N>/          finished deliverables of earlier parts (do not edit)
data/cache/             downloaded API data (Git-ignored, re-created by the notebook)
.streamlit/             config.toml (theme); secrets.toml is local and Git-ignored
```

Keep the repository root free of other files. Page order in `app.py` follows the assignment
(updated 12.10): 1 Home, 2 Data table, 3 Data plot, 4 Cross-border flows, 5 About.

## How to write code

- **Page pattern.** Each page file has a module docstring, small named functions and one
  `render_page()` that is called at the bottom. No logic at module level apart from that call.
- **Small functions.** If a block is longer than about 10 lines or has its own purpose (load,
  filter, plot, show), extract it into a function with a descriptive name.
- **Docstrings and comments, always.** Every function has a one-line docstring that says what it
  returns or shows. Comments explain *why* (units, time zones, API quirks), not what the syntax does.
- **Type hints** on all function parameters and return values (`pd.DataFrame`, `Figure`, `None`, …).
- **Shared code.** Data access, controls and styling live in `src/utils/`. Reuse `load_data()`,
  `reservoir_controls()`, `page_header()`, `chart_style()` and `show_figure()` instead of rewriting them.
- **Plots:** Seaborn/Matplotlib with `chart_style()`. One line per area or link. Label the axes with units.
- **Notebook:** every cell starts with a comment; markdown before each section explains the
  purpose and the findings. Run all cells before the PDF export.

## Do NOT

- Do **not** duplicate code that already exists in `src/utils/`. Extend the shared helper instead.
- Do **not** commit, print or ask for secrets (passwords, tokens, connection strings). Error
  messages must not show request URLs that contain the ENTSO-E token.
- Do **not** put different units on one y-axis, or draw one line through several areas.
- Do **not** change the visible behaviour of existing pages or move files without first
  describing the change to the student and getting an OK.
- Do **not** push to `main` or merge without the student's approval. Work on the part branch
  (Part 2: `codex/ind320-part2`).
- Do **not** write the work log or the AI-usage statement as if you were the student. Give facts.
- Do **not** commit `notes/` (private notes) or files in `data/cache/`.

## Data facts that are easy to get wrong

- NVE `dato_Id` is the Sunday that ends the ISO week. `neste_Publiseringsdato` year `0001` means no date.
  Always pass an explicit format to `pd.to_datetime`.
- The NVE API has no query parameters: every call returns the full history.
- ENTSO-E physical flows are MW per direction (not netted), at 15 or 60 minute resolution. Convert to
  MWh with the resolution before summing. One request may cover at most one year.
- Store times in UTC; derive year and month in `Europe/Oslo`.

## Commands

```bash
uv venv --python 3.12 .venv && uv pip install -r notebooks/requirements.txt
.venv/bin/python -m streamlit run app.py
docker start my_cassandra   # first time: docker run --name my_cassandra -p 9042:9042 -d cassandra:latest
```

Versions follow the course book: Python 3.12, PySpark 3.5.1 with
`spark-cassandra-connector_2.12:3.5.1`, Java 17. PySpark 3.5 needs `import setuptools` before
`pyspark` on Python 3.12, because it still imports `distutils`.

## Documentation

- Streamlit API: https://docs.streamlit.io/develop/api-reference
  (`st.navigation`, `st.columns`, `st.radio`, `st.pills`, `st.slider`, `st.expander`, `st.secrets`, caching)
- pandas: https://pandas.pydata.org/docs/reference/ · Seaborn: https://seaborn.pydata.org/api.html
- PySpark SQL: https://spark.apache.org/docs/3.5.1/api/python/reference/pyspark.sql/
- Spark Cassandra Connector: https://github.com/datastax/spark-cassandra-connector
- PyMongo: https://pymongo.readthedocs.io/ · MongoDB aggregation: https://www.mongodb.com/docs/manual/aggregation/
- Course book: https://github.com/khliland/IND320 (`D2Dbook/2_Data_sources/2_Databases`, `7_Appendix/Installation.ipynb`)
- NVE API: https://biapi.nve.no/magasinstatistikk/swagger/index.html
- ENTSO-E API: https://documenter.getpostman.com/view/7009892/2s93JtP3F6
