from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class LegendEntry:
    color_code: str
    interpretation: str


@dataclass(frozen=True)
class ColorCodedFact:
    row_idx: int
    col_idx: int
    color_code: str
    interpretation: str


@dataclass
class ColorCodedTable:
    page_number: int
    facts: list[ColorCodedFact] = field(default_factory=list)
    title: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    legend: list[LegendEntry] = field(default_factory=list)


@dataclass
class DocumentColorCodeExtraction:
    items: list[ColorCodedTable] = field(default_factory=list)
