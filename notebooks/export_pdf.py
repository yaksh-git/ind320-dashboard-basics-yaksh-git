"""Export the Part 2 notebook to PDF: nbconvert -> HTML, then headless Google Chrome -> PDF.

Run all notebook cells first, then from the repository root:

    .venv/bin/python notebooks/export_pdf.py

The HTML and PDF are written to output/ (ignored by Git). Chrome is used because it is already
installed; no extra download (LaTeX or a Playwright browser) is needed.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "ind320_part2.ipynb"
OUTPUT = ROOT / "output"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# On paper there is no sideways scrolling: wrap long code and output lines instead of cutting
# them off, use A4 pages, and keep each figure on one page.
PRINT_CSS = """<style>
@page { size: A4; margin: 14mm 12mm; }
@media print {
  pre, code { white-space: pre-wrap !important; overflow-wrap: anywhere; }
  .jp-OutputArea-output pre { font-size: 85%; }
  img { break-inside: avoid; max-width: 100% !important; }
}
</style>
"""


def export_html() -> Path:
    """Convert the executed notebook to HTML and add the print style sheet."""
    subprocess.run([sys.executable, "-m", "nbconvert", "--to", "html", "--output-dir", str(OUTPUT),
                    "--output", NOTEBOOK.stem, str(NOTEBOOK)], check=True)
    html = OUTPUT / f"{NOTEBOOK.stem}.html"
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
    print("Wrote", print_pdf(export_html()).relative_to(ROOT))
