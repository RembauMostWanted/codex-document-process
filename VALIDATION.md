# MAS document validation

Validation completed on 5 September 2026 against all ten PDFs in `data/`.
The manual environment setup completed successfully, `uv sync --extra test`
resolved 24 packages, all automated tests passed, and directory processing
created one JSON file beside every PDF.

## Commands and dependency checks

```console
/opt/codex/setup_universal.sh
# Configuring language runtimes...

uv sync --extra test
# Resolved 24 packages; audited 20 packages

uv run --no-sync pytest
# 16 passed

uv run --no-sync python -m cli --dir data
# Generated all ten *_color_code.json files; exit status 0

uv tree | rg -i 'pymupdf|fitz'
uv pip list | rg -i 'pymupdf|fitz'
rg -n -i 'pymupdf|fitz' --glob '!*.pdf' --glob '!VALIDATION.md' .
# All three searches returned no matches
```

Neither the resolved dependency graph nor the installed environment contains
PyMuPDF/fitz, and production code contains no import or reference to it. The
backend is `pdfplumber`/`pdfminer.six`.

## Per-document results

| Document | Tables | Facts | Source-page investigation |
|---|---:|---:|---|
| FSR 2016.pdf | 0 | 0 | Inspected page 48, previously misidentified: it contains stacked bar charts and legends, not blank colour-coded table cells. |
| FSR 2017.pdf | 0 | 0 | Inspected page 68, previously misidentified: the grey regions are ordinary regression-table shading. |
| FSR 2018.pdf | 0 | 0 | Inspected page 43, previously misidentified: coloured rectangles are chart bars and legend marks. |
| Financial Stability Review 2019.pdf | 0 | 0 | Inspected formerly detected page 73; detections came from plotted chart elements rather than colour-coded blank cells. |
| Financial Stability Review 2020.pdf | 1 | 2 | Page 9 overview table visually confirms pale-blue blank cells for Overall Corporate FVI and Overall Banking FVI. The orange Household FVI cell is visible but is not emitted because its legend band has no directly associated text span. |
| Financial Stability Review 2021.pdf | 0 | 0 | Inspected pages 87 and 118: alternating row/column shading and blank regression cells were false positives, not semantic colour facts. |
| Financial Stability Review 2022.pdf | 0 | 0 | Inspected prior candidate pages 54, 62, and 68; plotted shapes/table decoration did not provide reliable blank-cell colour-code evidence. |
| Financial Stability Review 2023.pdf | 0 | 0 | Inspected page 23: it is a normal risk-ranking table, and white cells must not be interpreted as colour facts. |
| Financial Stability Review 2024.pdf | 3 | 28 | Pages 20, 28, and 36 contain FVI tables; page 54's grey lower triangle was investigated and rejected as intentionally unavailable portfolio comparisons. |
| Financial Stability Review 2025.pdf | 3 | 28 | Pages 28, 34, and 39 contain the corporate, household, and banking FVI tables respectively. Pages 26, 55, and 59 were investigated and rejected as ordinary tabular formatting. |

## Representative source checks

The checks below compare PDF-rendered pages with the committed JSON, rather
than assuming a non-empty or empty result is correct.

* **2020 page 9:** Corporate FVI and Banking FVI are visibly pale blue
  (`#D9E1F2`) and both appear in JSON. Household FVI is orange; the known
  omission is recorded above rather than being silently treated as correct.
* **2024 page 20:** the five-row, two-period corporate FVI grid produces ten
  facts. Representative visual matches include row 0 green then salmon and row
  2 teal then pale blue.
* **2024 page 28:** the four-row household FVI grid produces eight facts, with
  the first row teal in both periods and the second row green then teal.
* **2025 page 28:** the five-row corporate FVI grid produces exactly ten facts.
  The rendered source confirms row 0 pale blue then green, row 3 green then
  teal, and row 4 salmon then pale blue.
* **2025 pages 34 and 39:** the household grid has eight cells and the banking
  grid has ten cells; those counts and representative teal/green/pale-blue
  fills agree with JSON.

Interpretation strings are the nearest text labels recoverable from the PDF's
positioned legend. The MAS five-band legends label their endpoints and centre,
not every individual band, so adjacent intermediate colours can share the
nearest extracted label. The hexadecimal colour and row/column location remain
the primary evidence in these outputs.

## Correctness fixes prompted by document inspection

Actual-PDF inspection exposed three false-positive classes that unit fixtures
did not originally cover: narrow chart bars, nested duplicate rectangles, and
monochrome decorative table shading. The extractor now rejects undersized
chart marks and near-white cells, collapses same-colour nested rectangles,
requires more than one legend colour, and rejects sizeable monochrome runs.
Regression tests cover duplicate/bar and monochrome-shading cases.
