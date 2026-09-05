# PDF colour-coded fact extraction

`pdf-color-facts` extracts facts from PDF table cells whose otherwise blank
contents are represented by a fill colour. It requires evidence from a nearby,
multi-entry colour legend before emitting a fact, so ordinary blank or coloured
layout elements are not automatically promoted to data.

## Setup

Install the project dependencies, including the test tools, with
[uv](https://docs.astral.sh/uv/):

```shell
uv sync --extra test
```

The project uses a `src` layout and its package configuration discovers both
the extraction library and CLI. No `PYTHONPATH` override is needed.

## Command line

Process one PDF from the repository root:

```shell
uv run python -m cli --fpath "data/report.pdf"
```

Or process every immediate `.pdf` file in a directory (case-insensitively and
in deterministic filename order):

```shell
uv run python -m cli --dir "data"
```

Exactly one input option is required. Directory traversal is not recursive.
Each generated path is printed. If one document in directory mode fails, the
remaining PDFs are still processed; failures are summarized and the command
exits nonzero. A missing input, invalid path, directory with no PDFs, or failed
single-file extraction also exits nonzero.

## Python API

The runner has no dependency on the CLI and can be embedded in another Python
service:

```python
from pdf_color_facts import ColorCodeRunner

runner = ColorCodeRunner("data/Financial Stability Review 2025.pdf")
result = runner.run()
print(runner.output_path)

for table in result.items:
    for fact in table.facts:
        print(table.page_number, fact.row_idx, fact.col_idx,
              fact.color_code, fact.interpretation)
```

The existing extraction-only API remains available when JSON output is not
wanted:

```python
from pdf_color_facts import extract_color_coded_facts

result = extract_color_coded_facts("data/Financial Stability Review 2025.pdf")
```

The public `extract_from_pages` function accepts backend-neutral positioned
text and fill primitives. This makes the evidence rules independently testable
and permits alternative PDF parsers. The default file API uses PyMuPDF and
extracts vector fills; scanned/raster-only tables require OCR/vectorisation
before calling the engine.

## JSON output

Output is written beside the input as `<pdf_stem>_color_code.json`; for example,
`data/report.pdf` produces `data/report_color_code.json`. The UTF-8, indented
JSON preserves the complete extraction object and its existing field names:

```json
{
  "items": [
    {
      "page_number": 1,
      "facts": [
        {
          "row_idx": 0,
          "col_idx": 1,
          "color_code": "#005A5A",
          "interpretation": "Lower vulnerability"
        }
      ],
      "title": "Risk dashboard",
      "bbox": {"x0": 120.0, "y0": 100.0, "x1": 180.0, "y1": 132.0},
      "legend": [
        {"color_code": "#005A5A", "interpretation": "Lower vulnerability"}
      ]
    }
  ]
}
```

An empty extraction is `{"items": []}` (formatted across multiple lines in
the file). Output replacement is atomic and occurs only after extraction and
serialization succeed. The source PDF is never changed.

## Development

```shell
uv run pytest
```
