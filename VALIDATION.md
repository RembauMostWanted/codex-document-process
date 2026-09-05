# MAS document validation

Validation was attempted on 5 September 2026 against the ten PDF files in
`data/`. This checkout's execution environment could not resolve the updated
dependencies: its configured network proxy returned HTTP 403 for PyPI and no
pdfplumber/pdfminer installation was present locally. Consequently the actual
document run could not start. No JSON files were created, because creating
success-looking output for documents that were not processed would be
misleading.

## Commands

```console
uv sync --extra test
uv run python -m cli --dir data
uv run pytest
uv tree | rg -i 'pymupdf|fitz'
rg -n -i 'pymupdf|fitz' --glob '!*.pdf' .
```

Only the first command could be attempted. It failed while fetching
`pdfplumber` (and, on separate attempts, `pytest` and `typer`) with `CONNECT
tunnel failed, response 403`; commands that require the environment therefore
could not be run. The source-only extractor and runner tests were executed with
the preinstalled global pytest and passed (`6 passed`). A static repository
search found no remaining PyMuPDF or `fitz` references outside this report.

## Per-document status

All entries below are **execution failures**, not successful empty
extractions. Table and fact counts and source-page checks are therefore not
available.

| Document | Status | Tables | Facts | Output | Error / limitation |
|---|---:|---:|---:|---|---|
| FSR 2016.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| FSR 2017.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| FSR 2018.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2019.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2020.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2021.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2022.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2023.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2024.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |
| Financial Stability Review 2025.pdf | Failed | N/A | N/A | Not created | Updated dependency environment unavailable |

## Correctness status

The backend implementation and its colour conversions have unit coverage, but
actual-document correctness is **not verified**. In particular, no legend
meaning, fill colour, or row/column position has been accepted as verified
without comparison to its rendered source page. This report must be replaced
with successful per-document results and representative page checks once an
environment capable of installing the declared dependencies is available.
