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
        "OpenAI Codex generated most of the initial Python code, the Streamlit app, "
        "the Jupyter Notebook structure and plots, code comments, and a draft of "
        "this work log. It also downloaded the course CSV, ran the notebook and "
        "local app tests, created the GitHub repository, deployed the Streamlit app, "
        "and prepared a PDF for review. I supplied the assignment text, chose to "
        "use AI, provided my GitHub details, and authorized publication. I must "
        "review the code, results, and wording myself before submission and take "
        "responsibility for the final work. **Update this description if you use Claude or other AI tools or "
        "make further changes before submitting.**"
    ),
    nbf.v4.new_markdown_cell(
        """## 6. Arbeidslogg (utkast – kontroller og tilpass før innlevering)

Arbeidet med første del av IND320 startet med at jeg delte kravene fra Canvas med OpenAI Codex. Jeg valgte å bruke verktøyet til å skrive hoveddelen av koden og et utkast til dokumentasjonen. Codex fant datafilen `reservoirs.csv` i faglærerens GitHub-repo og laget både Jupyter Notebook og Streamlit-appen. Bruken av AI er beskrevet mer detaljert over. Før innlevering må jeg selv kontrollere at denne loggen gjenspeiler det jeg faktisk har gjort, og legge til erfaringene fra siste gjennomgang og skjermopptak.

I notebooken blir CSV-filen lest med Pandas, og alle de norske kolonnenavnene blir oversatt til engelske navn som er lettere å bruke videre i koden. Datasettet inneholder flere geografiske serier for hver uke. Derfor brukes serien for Norge totalt når verdier vises over tid, mens hele datasettet brukes når kategoriene skal telles. Jeg viser de første og siste radene, datatyper, manglende verdier og en statistisk oppsummering. Dette gir et mer lesbart inntrykk av innholdet enn å skrive ut alle radene. Hver kolonne får sin egen figur. For kolonner med tall brukes tidsserier, mens kategorier og datoer vises på en måte som passer datatypen. Til slutt vises tallkolonnene sammen etter min–maks-normalisering, siden de har ulike enheter og skalaer. Alle kodecellene ble kjørt og kontrollert uten feil, slik at tabeller og figurer er lagret i notebooken.

Streamlit-appen er bygget som fire separate sider med navigasjon i sidepanelet. Startsiden forklarer prosjektet, tabellsiden har én rad per CSV-kolonne og små linjediagrammer for den første måneden, og plotsiden lar brukeren velge kolonne og et intervall av måneder. Den fjerde siden er foreløpig en enkel plassholder, slik oppgaven åpner for. Data leses fra en lokal CSV-fil og mellomlagres med Streamlits cache-funksjon. Det var viktig å skille mellom den fullstendige tabellen og den nasjonale tidsserien; ellers kunne kurven ha hoppet mellom ulike geografiske områder. Codex kjørte alle fire sidene i en lokal app-test, testet et konkret kolonnevalg og et månedsintervall og kontrollerte at tabellen viste elleve rader.

Med min godkjenning la Codex prosjektfilene i et offentlig GitHub-repo og koblet Streamlit Cloud til `app.py` på hovedgrenen. De faktiske lenkene står øverst i notebooken. Codex åpnet nettappen og kontrollerte alle fire sidene etter publisering. Før levering gjenstår min egen gjennomlesning av notebook og PDF og et kort skjermopptak. Jeg må også justere formuleringer i denne loggen som ikke stemmer med min egen erfaring.
"""
    ),
]

notebook = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
nbf.write(notebook, Path("dashboard_basics.ipynb"))
print("Wrote dashboard_basics.ipynb")
