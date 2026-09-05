from pathlib import Path

from .models import BoundingBox
from .primitives import FilledRectangle, Page, TextSpan


def read_pages(path: str | Path) -> list[Page]:
    """Read vector fills and positioned text with PyMuPDF.

    Importing is deliberately delayed so callers can use the backend-neutral
    extraction engine without installing a PDF library.
    """
    import fitz

    pages: list[Page] = []
    with fitz.open(path) as document:
        for page_number, pdf_page in enumerate(document, 1):
            texts = []
            for block in pdf_page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        value = span["text"].strip()
                        if value:
                            texts.append(TextSpan(value, BoundingBox(*span["bbox"])))
            fills = []
            for drawing in pdf_page.get_drawings():
                fill = drawing.get("fill")
                if fill is None:
                    continue
                rgb = tuple(round(max(0.0, min(1.0, channel)) * 255) for channel in fill[:3])
                rectangles = [item[1] for item in drawing.get("items", []) if item[0] == "re"]
                # Non-rectangular filled paths still have a useful bounding box.
                # For a compound path, however, preserve its individual `re`
                # cells rather than turning an entire table into one rectangle.
                if not rectangles:
                    rectangles = [drawing["rect"]]
                for rect in rectangles:
                    if rect.width > 1 and rect.height > 1:
                        fills.append(FilledRectangle(BoundingBox(rect.x0, rect.y0, rect.x1, rect.y1), rgb))
            pages.append(Page(page_number, pdf_page.rect.width, pdf_page.rect.height, texts, fills))
    return pages
