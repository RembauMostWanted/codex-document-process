# MAS document validation

Validation completed on 5 September 2026 against all ten PDFs in `data/`.
Extraction completed successfully for every file. The fact claims below are
separately identified as visually verified; successful execution by itself is
not evidence of document-wide extraction completeness.

## Commands and checks

```console
uv sync --extra test
# Resolved 24 packages

uv run --no-sync pytest -q
# 21 passed in 0.47s

find data -maxdepth 1 -type f -iname '*.pdf' -print0 \
  | xargs -0 -n1 -P6 uv run --no-sync python -m cli --fpath
# Generated all ten sibling *_color_code.json files; exit status 0

uv tree | rg -i 'pymupdf|fitz'
uv pip list | rg -i 'pymupdf|fitz'
rg -n -i 'pymupdf|fitz' --glob '!*.pdf' --glob '!VALIDATION.md' .
# All three searches returned no matches

uv run --no-sync python - <<'PY'
import pdfplumber
for filename, page_number in [
    ("Financial Stability Review 2020.pdf", 9),
    ("Financial Stability Review 2024.pdf", 20),
    ("Financial Stability Review 2025.pdf", 28),
]:
    with pdfplumber.open("data/" + filename) as pdf:
        pdf.pages[page_number - 1].to_image(resolution=110).save(
            f"/tmp/{filename[:4]}-p{page_number}.png"
        )
PY
# Rendered the three pages used for the visual checks below
```

The backend and resolved environment use `pdfplumber`/`pdfminer.six`, not
PyMuPDF/fitz.

## Before/after results

| Document | Before facts | After facts | After tables | Investigation status |
|---|---:|---:|---:|---|
| FSR 2016.pdf | 0 | 0 | 0 | Prior page 48 chart candidate remains rejected; an empty result is not a document-wide absence claim. |
| FSR 2017.pdf | 0 | 0 | 0 | Prior page 68 decorative regression shading remains rejected; completeness unverified. |
| FSR 2018.pdf | 0 | 0 | 0 | Prior page 43 chart bars remain rejected; completeness unverified. |
| Financial Stability Review 2019.pdf | 0 | 0 | 0 | Page 73 chart markers remain rejected; completeness unverified. |
| Financial Stability Review 2020.pdf | 2 | 3 | 1 | Page 9 table and legend visually verified, including the recovered orange cell. |
| Financial Stability Review 2021.pdf | 0 | 0 | 0 | Prior pages 87 and 118 decorative fills remain rejected; completeness unverified. |
| Financial Stability Review 2022.pdf | 0 | 0 | 0 | Prior pages 54, 62, and 68 chart/decoration candidates remain rejected; completeness unverified. |
| Financial Stability Review 2023.pdf | 0 | 0 | 0 | Prior page 23 white table cells remain rejected; completeness unverified. |
| Financial Stability Review 2024.pdf | 28 | 28 | 3 | Representative page 20 visually verified; pages 28 and 36 use the same five-band legend structure. |
| Financial Stability Review 2025.pdf | 28 | 28 | 3 | Representative page 28 visually verified; pages 34 and 39 use the same five-band legend structure. |

## Specific visual verification

* **2020 PDF page 9:** the physical rows are Corporate, Household, and Banking.
  JSON now emits `(row_idx, col_idx)` values `(0, 1)`, `(1, 1)`, and `(2, 1)`.
  Corporate and Banking are pale blue and exactly `Broadly Unchanged`.
  Household is light orange; the printed five-band legend labels only the
  first, centre, and last bands, so its exact label is honestly recorded as
  `Unresolved between Broadly Unchanged and Increased significantly`.
* **2024 PDF page 20:** all ten cells visually match the two physical data
  columns and five physical rows. Teal is `Lower vulnerability`, pale blue is
  `Average vulnerability`, and the intermediate green and salmon bands are
  explicitly unresolved between their labelled neighbours. The heading `FVI
  level quintiles` is not an interpretation and each swatch occurs once.
* **2025 PDF page 28:** the ten emitted positions and colours match the rendered
  five-by-two corporate FVI table. Its meanings follow the same endpoint,
  centre, and unresolved-intermediate treatment as the printed legend.

## Scope and remaining limitations

Verified facts are limited to the pages and cells named above. Empty output
means no facts met the current vector-rectangle, blank-cell, table-grid, and
legend evidence rules; it does **not** establish that the entire report lacks
colour-coded tables. Raster-only content, non-rectangular path fills, legends
whose structure cannot be established, and layouts without usable row labels
remain unsupported. The deliberately conservative unresolved values preserve
source evidence but do not infer unpublished names for intermediate bands.
