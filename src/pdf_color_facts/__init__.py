"""Extract semantic facts represented by fill colours in PDF tables."""

from .extractor import extract_color_coded_facts, extract_from_pages
from .models import (
    BoundingBox,
    ColorCodedFact,
    ColorCodedTable,
    DocumentColorCodeExtraction,
    LegendEntry,
)
from .runner import ColorCodeRunner

__all__ = [
    "BoundingBox",
    "ColorCodedFact",
    "ColorCodedTable",
    "ColorCodeRunner",
    "DocumentColorCodeExtraction",
    "LegendEntry",
    "extract_color_coded_facts",
    "extract_from_pages",
]
