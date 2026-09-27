"""Generate the IND320 analysis notebook from documented, runnable cells."""

from pathlib import Path

import nbformat as nbf


cells = [
    nbf.v4.new_markdown_cell(
        "# IND320 — Dashboard basics\n\n"
        "Reservoir data analysis for the first compulsory hand-in. "
        "The source file is the course's `D2Dbook/data/reservoirs.csv`."
    ),
    nbf.v4.new_markdown_cell(
        "## Project links\n\n"
        "- Public GitHub repository: https://github.com/yaksh-git/ind320-dashboard-basics-yaksh-git\n"
        "- Streamlit app: https://ind320-dashboard-basics-yaksh-git.streamlit.app/"
    ),
    nbf.v4.new_markdown_cell(
        "## 1. Load and rename the data\n\n"
        "The source contains nine geographic series for each reporting week. "
        "For line plots, this notebook uses the supplied Norway total (`NO`, area `0`) "
        "so that each line represents one consistent area. The full imported data "
        "remains available in `data`."
    ),
    nbf.v4.new_code_cell(
        "from pathlib import Path\n"
        "import os\n"
        "import pandas as pd\n"
        "# Use a writable project cache before importing Matplotlib on Windows.\n"
        "mpl_cache = Path('.matplotlib')\n"
        "mpl_cache.mkdir(exist_ok=True)\n"
        "os.environ['MPLCONFIGDIR'] = str(mpl_cache.resolve())\n"
        "import matplotlib.pyplot as plt\n\n"
        "# Keep the CSV in the same folder as this notebook.\n"
        "csv_path = Path('reservoirs.csv')\n"
        "data = pd.read_csv(csv_path)\n\n"
        "# Translate all source headers once; use these names in later cells.\n"
        "column_names = {\n"
        "    'dato_Id': 'date',\n"
        "    'omrType': 'area_type',\n"
        "    'omrnr': 'area_number',\n"
        "    'iso_aar': 'iso_year',\n"
        "    'iso_uke': 'iso_week',\n"
        "    'fyllingsgrad': 'fill_level',\n"
        "    'kapasitet_TWh': 'capacity_twh',\n"
        "    'fylling_TWh': 'stored_energy_twh',\n"
        "    'neste_Publiseringsdato': 'next_publication_date',\n"
        "    'fyllingsgrad_forrige_uke': 'previous_week_fill_level',\n"
        "    'endring_fyllingsgrad': 'fill_level_change',\n"
        "}\n"
        "data = data.rename(columns=column_names)\n"
        "data['date'] = pd.to_datetime(data['date'], errors='coerce')\n"
        "data = data.sort_values(['date', 'area_type', 'area_number']).reset_index(drop=True)\n"
        "national = data.loc[(data['area_type'] == 'NO') & (data['area_number'] == 0)].copy()\n"
        "print(f'{len(data):,} rows, {len(data.columns)} columns')\n"
        "print(f'{national.date.min():%Y-%m-%d} to {national.date.max():%Y-%m-%d}')"
    ),
    nbf.v4.new_markdown_cell(
        "## 2. Inspect the contents\n\n"
        "Show representative rows, column types, missing values and numeric summaries. "
        "This is more useful than printing all 14,877 rows."
    ),
    nbf.v4.new_code_cell(
        "# Show useful fields from the beginning and end of the sorted source.\n"
        "preview_columns = ['date', 'area_type', 'area_number', 'fill_level',\n"
        "                   'capacity_twh', 'stored_energy_twh']\n"
        "display(data[preview_columns].head(10))\n"
        "display(data[preview_columns].tail(10))\n"
        "display(pd.DataFrame({'dtype': data.dtypes.astype(str), 'missing': data.isna().sum()}))\n"
        "# A compact numeric summary fits both the notebook and PDF page.\n"
        "display(data.select_dtypes(include='number').describe().T[['count', 'mean', 'std', 'min', 'max']])"
    ),
    nbf.v4.new_markdown_cell(
        "## 3. Plot every column separately\n\n"
        "Numeric values are shown as time series for Norway total. "
        "The date field is shown as counts by year, geographic identifiers as "
        "bar charts, and the publication field as a valid/missing count. "
        "The source uses year `0001` to mean that no next publication date is supplied."
    ),
    nbf.v4.new_code_cell(
        "# Plot the date column as number of national observations per year.\n"
        "counts = national['date'].dt.year.value_counts().sort_index()\n"
        "ax = counts.plot.bar(figsize=(11, 3), title='date — observations per year')\n"
        "ax.set(xlabel='Year', ylabel='Observations')\n"
        "plt.tight_layout(); plt.show()"
    ),
    nbf.v4.new_code_cell(
        "# Plot both geographic identifier columns using all records.\n"
        "for column in ['area_type', 'area_number']:\n"
        "    ax = data[column].value_counts().sort_index().plot.bar(figsize=(7, 3), title=column)\n"
        "    ax.set(xlabel=column, ylabel='Rows')\n"
        "    plt.tight_layout(); plt.show()"
    ),
    nbf.v4.new_code_cell(
        "# Plot each numeric column separately for one coherent geographic series.\n"
        "numeric_columns = ['iso_year', 'iso_week', 'fill_level', 'capacity_twh',\n"
        "                   'stored_energy_twh', 'previous_week_fill_level', 'fill_level_change']\n"
        "for column in numeric_columns:\n"
        "    fig, ax = plt.subplots(figsize=(11, 3))\n"
        "    ax.plot(national['date'], national[column], linewidth=0.8)\n"
        "    ax.set(title=column, xlabel='Date', ylabel=column)\n"
        "    ax.grid(alpha=0.25)\n"
        "    fig.autofmt_xdate()\n"
        "    plt.tight_layout(); plt.show()"
    ),
    nbf.v4.new_code_cell(
        "# Year 0001 is outside pandas' datetime range and means no usable date.\n"
        "next_date = pd.to_datetime(data['next_publication_date'],\n"
        "                           format='%Y-%m-%dT%H:%M:%S', errors='coerce')\n"
        "publication_counts = pd.Series({'Provided': next_date.notna().sum(),\n"
        "                                'Unavailable': next_date.isna().sum()})\n"
        "ax = publication_counts.plot.bar(figsize=(6, 3), title='next_publication_date')\n"
        "ax.set(xlabel='Status', ylabel='Rows')\n"
        "plt.tight_layout(); plt.show()"
    ),
    nbf.v4.new_markdown_cell(
        "## 4. Plot all numeric columns together\n\n"
        "The columns have different units and ranges. Min–max scaling maps each "
        "nonconstant column to 0–1, making its shape comparable without implying "
        "that the original units are the same. This plot shows relative changes, "
        "not absolute reservoir levels."
    ),
    nbf.v4.new_code_cell(
        "# Normalize the national series column by column; omit constants.\n"
        "values = national[numeric_columns]\n"
        "ranges = values.max() - values.min()\n"
        "varying = ranges[ranges > 0].index\n"
        "scaled = (values[varying] - values[varying].min()) / ranges[varying]\n"
        "fig, ax = plt.subplots(figsize=(12, 5))\n"
        "for column in varying:\n"
        "    ax.plot(national['date'], scaled[column], linewidth=0.8, label=column)\n"
        "ax.set(title='All numeric columns — normalized, Norway total',\n"
        "       xlabel='Date', ylabel='Normalized value (0–1)')\n"
        "ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))\n"
        "ax.grid(alpha=0.25)\n"
        "fig.autofmt_xdate()\n"
        "plt.tight_layout(); plt.show()"
    ),
    nbf.v4.new_markdown_cell(
        "## 5. AI usage\n\n"
        "The course encourages the use of AI tools. I chose OpenAI Codex with GPT-6 "
        "for this project, although I also have access to Claude Code. I used Codex "
        "both to build a first version and to ask how and why the notebook, plots, "
        "Streamlit pages, and deployment work. Codex generated most of the initial "
        "Python and Streamlit code, notebook structure, comments, and a draft of this "
        "log. It also obtained the course CSV, ran checks, set up the public GitHub "
        "repository and Streamlit app with my approval, and prepared a PDF for review. "
        "I pulled the course repository to my computer and connected Codex to my "
        "local project. I asked follow-up questions, inspected outputs, reported "
        "warnings, and requested fixes. I explicitly approved the public publication "
        "steps rather than enabling automatic approval. I am responsible for checking "
        "the final code, results, text, and screencast before submission."
    ),
    nbf.v4.new_markdown_cell(
        """## 6. Work log

I began Part 1 by reading the Canvas instructions and pulling the course repository into a local folder on my computer. I connected Codex to the local project and shared the assignment requirements. The instructions explicitly encourage AI tools, and I wanted to try the GPT-6 models in Codex for this assignment, even though I also have Claude Code. I used AI to explore how the code works and checked whether its output met the requirements. Developers in our company also use AI extensively and review its results manually. In this project, I asked Codex questions about what a Jupyter Notebook is, why it was needed, and how the code and app fit together. Codex generated most of the first implementation, while I guided the task and asked for explanations and corrections.

In the notebook, Pandas reads `reservoirs.csv` and renames the Norwegian headers to English. I can inspect selected rows, data types, missing values, and summary statistics. The CSV contains several geographic areas for each week, so the time series use the supplied Norway total instead of mixing areas. Each column is plotted separately using a suitable form for its data type. A combined plot scales the numeric columns between zero and one because their units and ranges differ. This lets me compare their patterns without suggesting that their original values are directly comparable. I ran the cells and looked at the tables and plots. When a date parsing warning appeared, I asked why it happened and had the format specified explicitly. I also reported a Matplotlib cache warning, which led to a writable cache location being configured.

The Streamlit app has four pages. The home page provides sidebar navigation; the data table has one row per imported column and first-month sparklines for numeric values. The plot page lets me select a column or all numeric columns and choose a month range. The fourth page is a placeholder for later parts of the course. The app reads the local CSV and caches the data. Codex ran local checks of the pages and controls, and I opened the online app to inspect how it behaved.

I explicitly approved the public GitHub repository and Streamlit publication steps. Codex handled the technical setup, testing, and deployment; I did not enable automatic approval for those public actions. I have continued to ask what and why when reviewing the work. Before submitting, I will check the final notebook and PDF against the assignment and explain the code and my AI use in the screencast.
"""
    ),
]

notebook = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
nbf.write(notebook, Path("dashboard_basics.ipynb"))
print("Wrote dashboard_basics.ipynb")
