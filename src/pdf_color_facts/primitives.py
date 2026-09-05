"""Backend-neutral page primitives (also useful for deterministic tests)."""

from dataclasses import dataclass, field

from .models import BoundingBox


@dataclass(frozen=True)
class TextSpan:
    text: str
    bbox: BoundingBox


@dataclass(frozen=True)
class FilledRectangle:
    bbox: BoundingBox
    rgb: tuple[int, int, int]


@dataclass
class Page:
    number: int
    width: float
    height: float
    texts: list[TextSpan] = field(default_factory=list)
    fills: list[FilledRectangle] = field(default_factory=list)
