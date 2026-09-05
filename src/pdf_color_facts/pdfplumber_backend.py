"""PDF primitive adapter implemented with pdfplumber/pdfminer.six."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber

from .models import BoundingBox
from .primitives import FilledRectangle, Page, TextSpan


def _rgb(value: Any) -> tuple[int, int, int] | None:
    """Convert PDF gray/RGB/CMYK colour operands to 8-bit RGB."""
    if isinstance(value, (int, float)):
        channels = (float(value),) * 3
    elif isinstance(value, (tuple, list)) and len(value) == 1:
        channels = (float(value[0]),) * 3
    elif isinstance(value, (tuple, list)) and len(value) == 3:
        channels = tuple(float(channel) for channel in value)
    elif isinstance(value, (tuple, list)) and len(value) == 4:
        cyan, magenta, yellow, black = (float(channel) for channel in value)
        channels = (
            (1 - cyan) * (1 - black),
            (1 - magenta) * (1 - black),
            (1 - yellow) * (1 - black),
        )
    else:
        return None
    return tuple(round(max(0.0, min(1.0, channel)) * 255) for channel in channels)  # type: ignore[return-value]


def _text_spans(words: list[dict[str, Any]]) -> list[TextSpan]:
    """Join neighbouring words into the line fragments used by the engine."""
    remaining = [word for word in words if word["text"].strip()]
    spans: list[TextSpan] = []
    while remaining:
        first = remaining.pop(0)
        line = [first]
        while remaining:
            previous, candidate = line[-1], remaining[0]
            same_line = abs(float(candidate["top"]) - float(first["top"])) <= 2
            nearby = 0 <= float(candidate["x0"]) - float(previous["x1"]) <= 8
            if not (same_line and nearby):
                break
            line.append(remaining.pop(0))
        spans.append(
            TextSpan(
                " ".join(word["text"].strip() for word in line),
                BoundingBox(
                    float(first["x0"]),
                    min(float(word["top"]) for word in line),
                    float(line[-1]["x1"]),
                    max(float(word["bottom"]) for word in line),
                ),
            )
        )
    return spans


def read_pages(path: str | Path) -> list[Page]:
    """Read positioned words and filled vector rectangles with pdfplumber."""
    pages: list[Page] = []
    with pdfplumber.open(path) as document:
        for page_number, pdf_page in enumerate(document.pages, 1):
            words = pdf_page.extract_words(keep_blank_chars=False, use_text_flow=False)
            words.sort(key=lambda word: (round(float(word["top"]), 1), float(word["x0"])))
            texts = _text_spans(words)
            fills: list[FilledRectangle] = []
            for rectangle in pdf_page.rects:
                if not rectangle.get("fill"):
                    continue
                colour = _rgb(rectangle.get("non_stroking_color"))
                width = float(rectangle["x1"]) - float(rectangle["x0"])
                height = float(rectangle["bottom"]) - float(rectangle["top"])
                if colour is not None and width > 1 and height > 1:
                    fills.append(
                        FilledRectangle(
                            BoundingBox(
                                float(rectangle["x0"]),
                                float(rectangle["top"]),
                                float(rectangle["x1"]),
                                float(rectangle["bottom"]),
                            ),
                            colour,
                        )
                    )
            pages.append(Page(page_number, float(pdf_page.width), float(pdf_page.height), texts, fills))
    return pages
