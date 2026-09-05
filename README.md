# PDF colour-coded fact extraction

`pdf-color-facts` extracts facts from PDF table cells whose otherwise blank
contents are represented by a fill colour. It requires evidence from a nearby,
multi-entry colour legend before emitting a fact, so ordinary blank or coloured
layout elements are not automatically promoted to data.

```python
from pdf_color_facts import extract_color_coded_facts

result = extract_color_coded_facts("Financial Stability Review 2025.pdf")
for table in result.items:
    for fact in table.facts:
        print(table.page_number, fact.row_idx, fact.col_idx,
              fact.color_code, fact.interpretation)
```

The public `extract_from_pages` function accepts backend-neutral positioned
text and fill primitives. This makes the evidence rules independently testable
and permits alternative PDF parsers. The default file API uses PyMuPDF and
extracts vector fills; scanned/raster-only tables require OCR/vectorisation
before calling the engine.

## Development

```shell
python -m pip install -e '.[test]'
pytest
```
