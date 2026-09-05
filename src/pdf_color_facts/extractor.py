from __future__ import annotations

import math
from pathlib import Path

from .models import BoundingBox, ColorCodedFact, ColorCodedTable, DocumentColorCodeExtraction, LegendEntry
from .primitives import FilledRectangle, Page, TextSpan


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    # Normalised Euclidean RGB is intentionally conservative. PDF producer
    # roundoff is accepted, while visibly different legend categories are not.
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _overlaps(a: BoundingBox, b: BoundingBox, pad: float = 0) -> bool:
    return a.x0 < b.x1 + pad and a.x1 > b.x0 - pad and a.y0 < b.y1 + pad and a.y1 > b.y0 - pad


def _near_right(fill: FilledRectangle, texts: list[TextSpan]) -> TextSpan | None:
    box = fill.bbox
    candidates = [
        t
        for t in texts
        if t.bbox.x0 >= box.x1 - 1
        and t.bbox.x0 - box.x1 <= max(100, box.x1 - box.x0)
        and t.bbox.y0 < box.y1 + 3
        and t.bbox.y1 > box.y0 - 3
    ]
    return min(candidates, key=lambda t: t.bbox.x0, default=None)


def _legends(page: Page) -> list[tuple[FilledRectangle, TextSpan]]:
    entries = []
    for fill in page.fills:
        text = _near_right(fill, page.texts)
        if text and len(text.text) >= 2 and not any(_overlaps(fill.bbox, t.bbox) for t in page.texts):
            entries.append((fill, text))
    # A lone coloured label is not evidence of a colour-code system.
    usable = []
    for entry in entries:
        neighbours = [other for other in entries if other is not entry and abs(other[0].bbox.x0 - entry[0].bbox.x0) <= 30 and abs(other[0].bbox.y0 - entry[0].bbox.y0) <= page.height * .3]
        if neighbours:
            usable.append(entry)
    return usable


def _cluster(fills: list[FilledRectangle]) -> list[list[FilledRectangle]]:
    groups: list[list[FilledRectangle]] = []
    remaining = set(range(len(fills)))
    while remaining:
        todo = [remaining.pop()]
        group = []
        while todo:
            index = todo.pop()
            current = fills[index]
            group.append(current)
            close = [j for j in remaining if abs(fills[j].bbox.x0-current.bbox.x0) < 250 and abs(fills[j].bbox.y0-current.bbox.y0) < 120]
            for j in close:
                remaining.remove(j)
                todo.append(j)
        aligned = any(
            abs(a.bbox.x0 - b.bbox.x0) <= 3 or abs(a.bbox.y0 - b.bbox.y0) <= 3
            for position, a in enumerate(group)
            for b in group[position + 1 :]
        )
        if len(group) >= 2 and aligned:
            groups.append(group)
    return groups


def _ranks(values: list[float], tolerance: float = 3) -> dict[float, int]:
    centres: list[float] = []
    for value in sorted(values):
        if not centres or abs(value - centres[-1]) > tolerance:
            centres.append(value)
        else:
            centres[-1] = (centres[-1] + value) / 2
    return {value: min(range(len(centres)), key=lambda i: abs(centres[i] - value)) for value in values}


def extract_from_pages(pages: list[Page], *, color_tolerance: float = 18) -> DocumentColorCodeExtraction:
    """Extract facts from positioned page primitives.

    A fill is emitted only if (1) it is blank, (2) its colour matches a key in
    a multi-entry legend, and (3) it belongs to an aligned group of at least two
    candidate cells. These evidence gates avoid treating ordinary blank cells,
    decoration, and isolated highlights as facts.
    """
    result = DocumentColorCodeExtraction()
    for page in pages:
        legend_pairs = _legends(page)
        if len({entry[1].text.casefold() for entry in legend_pairs}) < 2:
            continue
        swatches = {id(fill) for fill, _ in legend_pairs}
        candidates = []
        meanings: dict[int, str] = {}
        for fill in page.fills:
            if id(fill) in swatches or any(_overlaps(fill.bbox, text.bbox) for text in page.texts):
                continue
            matches = [( _distance(fill.rgb, key.rgb), label.text) for key, label in legend_pairs]
            distance, meaning = min(matches, default=(float("inf"), ""))
            if distance <= color_tolerance:
                meanings[id(fill)] = meaning
                candidates.append(fill)
        for group in _cluster(candidates):
            xs = _ranks([f.bbox.x0 for f in group])
            ys = _ranks([f.bbox.y0 for f in group])
            box = BoundingBox(min(f.bbox.x0 for f in group), min(f.bbox.y0 for f in group), max(f.bbox.x1 for f in group), max(f.bbox.y1 for f in group))
            has_row_labels = any(t.bbox.x1 <= box.x0 + 5 and t.bbox.x1 >= box.x0 - 250 and t.bbox.y0 <= box.y1 and t.bbox.y1 >= box.y0 for t in page.texts)
            if not has_row_labels:
                continue
            facts = [ColorCodedFact(ys[f.bbox.y0], xs[f.bbox.x0] + 1, _hex(f.rgb), meanings[id(f)]) for f in sorted(group, key=lambda f: (f.bbox.y0, f.bbox.x0))]
            title_candidates = [t for t in page.texts if t.bbox.y1 <= box.y0 and box.y0 - t.bbox.y1 <= 80]
            title = max(title_candidates, key=lambda t: t.bbox.y1, default=None)
            legend = [LegendEntry(_hex(fill.rgb), text.text) for fill, text in legend_pairs]
            result.items.append(ColorCodedTable(page.number, facts, title.text if title else None, box, legend))
    return result


def extract_color_coded_facts(path: str | Path, *, color_tolerance: float = 18) -> DocumentColorCodeExtraction:
    """Extract colour-coded table facts from a PDF file."""
    from .pymupdf_backend import read_pages

    return extract_from_pages(read_pages(path), color_tolerance=color_tolerance)
