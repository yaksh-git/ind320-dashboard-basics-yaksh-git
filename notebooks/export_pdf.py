"""Export a notebook to PDF: nbconvert -> HTML, then headless Google Chrome -> PDF.

Run all notebook cells first, then from the repository root (the default is the Part 3 notebook):

    .venv/bin/python notebooks/export_pdf.py                       # notebooks/ind320_part3.ipynb
    .venv/bin/python notebooks/export_pdf.py ind320_part2.ipynb    # another notebook in notebooks/

The HTML and PDF are written to output/ (ignored by Git). Chrome is used because it is already
installed; no extra download (LaTeX or a Playwright browser) is needed.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NOTEBOOK = "ind320_part3.ipynb"
OUTPUT = ROOT / "output"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# On paper there is no sideways scrolling: wrap long code lines instead of cutting them off,
# print text output and tables a bit smaller so wide Spark/pandas tables fit the page width,
# use A4 pages, and keep each figure on one page.
PRINT_CSS = """<style>
@page { size: A4; margin: 14mm 12mm; }
@media print {
  pre, code { white-space: pre-wrap !important; overflow-wrap: anywhere; }
  .jp-OutputArea-output { overflow: visible !important; }
  .jp-OutputArea-output pre { font-size: 72% !important; }
  .jp-OutputArea-output table { font-size: 72% !important; }  /* output tables only, not markdown */
  img { break-inside: avoid; max-width: 100% !important; }
}
</style>
"""


def export_html(notebook: Path) -> Path:
    """Convert the executed notebook to HTML and add the print style sheet."""
    subprocess.run([sys.executable, "-m", "nbconvert", "--to", "html", "--output-dir", str(OUTPUT),
                    "--output", notebook.stem, str(notebook)], check=True)
    html = OUTPUT / f"{notebook.stem}.html"
    html.write_text(html.read_text(encoding="utf-8").replace("</head>", PRINT_CSS + "</head>", 1),
                    encoding="utf-8")
    return html


def print_pdf(html: Path) -> Path:
    """Print the HTML page to PDF with headless Chrome, using a throw-away browser profile."""
    pdf = html.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-first-run",
                        f"--user-data-dir={profile}", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf}", html.as_uri()],
                       check=True, capture_output=True)
    return pdf


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    notebook = ROOT / "notebooks" / (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NOTEBOOK)
    print("Wrote", print_pdf(export_html(notebook)).relative_to(ROOT))
