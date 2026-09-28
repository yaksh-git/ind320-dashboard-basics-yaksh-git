# IND320 Dashboard basics

Part 1 Streamlit app and Jupyter Notebook for the `reservoirs.csv` course data.

## Run locally

1. Install Python 3.12 or newer.
2. Create a virtual environment and install `requirements.txt`.
3. Run `streamlit run app.py`.

On Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

On macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

To execute the notebook and preserve output:

```bash
jupyter nbconvert --to notebook --execute --inplace dashboard_basics.ipynb
```

The app uses the local CSV and has four pages. The notebook is the analysis and
documentation deliverable. It should be run completely before PDF export.
Seaborn draws the time-series and category charts. The combined numeric view uses
separate panels because ISO fields, fractions, and TWh have different units.

## Submission checklist

- [x] Add the public GitHub repository and live Streamlit app URLs to the notebook.
- [ ] Read and confirm the 300–500-word English work log and AI-usage statement
      against your own experience before submission.
- [ ] Run all notebook cells and export the notebook to PDF.
- [x] Check all four pages on the deployed app, including table and plot controls.
- [ ] Record and share a five-minute screencast showing the app and explaining
      the main code.

Data source: [IND320 course repository](https://github.com/khliland/ind320/tree/main/D2Dbook/data).
