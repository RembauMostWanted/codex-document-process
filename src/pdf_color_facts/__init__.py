"""Extract semantic facts represented by fill colours in PDF tables."""

from .extractor import extract_color_coded_facts, extract_from_pages
from .models import (
    BoundingBox,
    ColorCodedFact,
    ColorCodedTable,
    DocumentColorCodeExtraction,
    LegendEntry,
)

__all__ = [
    "BoundingBox",
    "ColorCodedFact",
    "ColorCodedTable",
    "DocumentColorCodeExtraction",
    "LegendEntry",
    "extract_color_coded_facts",
    "extract_from_pages",
]
