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
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n"
        "sns.set_theme(style='whitegrid', context='notebook', palette='deep')\n\n"
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
        "A time series is a line ordered by date. Reservoir measurements and the "
        "ISO year/week fields use this form for the Norway total. The `date` column "
        "is already the horizontal coordinate, so its separate chart shows annual "
        "reporting frequency (the latest year may be incomplete). Geographic "
        "identifiers are categories, so they use "
        "count bars. The publication field uses counts of supplied and unavailable "
        "dates; year `0001` means no date was supplied."
    ),
    nbf.v4.new_code_cell(
        "# A date cannot be plotted against itself; count reports in each year.\n"
        "annual = national.groupby(national['date'].dt.year).size().rename('reports')\n"
        "annual = annual.rename_axis('year').reset_index()\n"
        "fig, ax = plt.subplots(figsize=(10, 3.5))\n"
        "sns.lineplot(data=annual, x='year', y='reports', marker='o',\n"
        "             color='#2563a6', errorbar=None, ax=ax)\n"
        "ax.set(title='Reporting frequency by year', xlabel='Year',\n"
        "       ylabel='Weekly reports for Norway total')\n"
        "ax.set_ylim(bottom=0)\n"
        "sns.despine()\n"
        "fig.tight_layout(); plt.show()"
    ),
    nbf.v4.new_code_cell(
        "# Area fields are categories, so count their occurrences in all rows.\n"
        "for column in ['area_type', 'area_number']:\n"
        "    fig, ax = plt.subplots(figsize=(8, 3.3))\n"
        "    sns.countplot(data=data, x=column, color='#3178a8', ax=ax)\n"
        "    ax.set(title=f'Records by {column}', xlabel=column, ylabel='CSV rows')\n"
        "    sns.despine()\n"
        "    fig.tight_layout(); plt.show()"
    ),
    nbf.v4.new_code_cell(
        "# Each numeric field is a time series for one coherent geographic area.\n"
        "numeric_columns = ['iso_year', 'iso_week', 'fill_level', 'capacity_twh',\n"
        "                   'stored_energy_twh', 'previous_week_fill_level', 'fill_level_change']\n"
        "labels = {'iso_year': ('ISO year', 'Year'),\n"
        "          'iso_week': ('ISO week', 'Week number'),\n"
        "          'fill_level': ('Reservoir fill level', 'Fraction full'),\n"
        "          'capacity_twh': ('Reservoir capacity', 'TWh'),\n"
        "          'stored_energy_twh': ('Stored energy', 'TWh'),\n"
        "          'previous_week_fill_level': ('Previous-week fill level', 'Fraction full'),\n"
        "          'fill_level_change': ('Weekly change in fill level', 'Fraction points')}\n"
        "for column in numeric_columns:\n"
        "    fig, ax = plt.subplots(figsize=(10, 3.2))\n"
        "    sns.lineplot(data=national, x='date', y=column, estimator=None,\n"
        "                 errorbar=None, color='#2563a6', linewidth=1.1, ax=ax)\n"
        "    ax.set(title=labels[column][0], xlabel='Date', ylabel=labels[column][1])\n"
        "    sns.despine()\n"
        "    fig.autofmt_xdate()\n"
        "    fig.tight_layout(); plt.show()"
    ),
    nbf.v4.new_code_cell(
        "# Year 0001 is outside pandas' datetime range and means no usable date.\n"
        "next_date = pd.to_datetime(data['next_publication_date'],\n"
        "                           format='%Y-%m-%dT%H:%M:%S', errors='coerce')\n"
        "publication_counts = pd.DataFrame({'status': ['Date supplied', 'No date (0001)'],\n"
        "                                   'rows': [next_date.notna().sum(), next_date.isna().sum()]})\n"
        "fig, ax = plt.subplots(figsize=(7, 3.3))\n"
        "sns.barplot(data=publication_counts, x='status', y='rows',\n"
        "            color='#3178a8', errorbar=None, ax=ax)\n"
        "ax.set(title='Next publication date availability', xlabel='', ylabel='CSV rows')\n"
        "sns.despine()\n"
        "fig.tight_layout(); plt.show()"
    ),
    nbf.v4.new_markdown_cell(
        "## 4. Plot all numeric columns together\n\n"
        "These seven numeric columns share one figure but have separate panels and "
        "vertical scales. This keeps TWh, fractions, years, and week numbers in "
        "their original units instead of overlaying unlike quantities. ISO year "
        "and week are time identifiers, not reservoir measurements."
    ),
    nbf.v4.new_code_cell(
        "# Small multiples show all numeric fields without mixing their units.\n"
        "fig, axes = plt.subplots(4, 2, figsize=(10, 10), sharex=True)\n"
        "for ax, column in zip(axes.flat, numeric_columns):\n"
        "    sns.lineplot(data=national, x='date', y=column, estimator=None,\n"
        "                 errorbar=None, linewidth=1, ax=ax)\n"
        "    ax.set(title=labels[column][0], xlabel='', ylabel=labels[column][1])\n"
        "    sns.despine(ax=ax)\n"
        "axes.flat[-1].axis('off')\n"
        "fig.suptitle('Numeric columns over time — Norway total', fontsize=16)\n"
        "fig.autofmt_xdate()\n"
        "fig.tight_layout(); plt.show()"
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

In the notebook, Pandas reads `reservoirs.csv` and renames the Norwegian headers to English. I can inspect selected rows, data types, missing values, and summary statistics. The CSV contains several geographic areas for each week, so the time series use the supplied Norway total instead of mixing areas. Each column is plotted separately using a suitable form for its data type. Seaborn is used to style the figures and draw the time series. A combined figure uses separate panels and vertical scales for the numeric columns because their units and ranges differ. I ran the cells and looked at the tables and plots. When a date parsing warning appeared, I asked why it happened and had the format specified explicitly. I also reported a Matplotlib cache warning, which led to a writable cache location being configured.

The Streamlit app has four pages. The home page provides sidebar navigation; the data table has one row per imported column and first-month sparklines for numeric values. The plot page lets me select a column or all numeric columns and choose a month range. The fourth page explains the area codes and units and can be extended in later parts. The app reads the local CSV and caches the data. Codex ran local checks of the pages and controls, and I opened the online app to inspect how it behaved. I also collaborated with a fellow student by comparing our plots and discussing why they looked different, especially the variables and scales shown.

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
