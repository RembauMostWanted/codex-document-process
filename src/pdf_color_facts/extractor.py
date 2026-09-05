from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from .models import BoundingBox, ColorCodedFact, ColorCodedTable, DocumentColorCodeExtraction, LegendEntry
from .primitives import FilledRectangle, Page, TextSpan


UNRESOLVED = "Unresolved"


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _area(box: BoundingBox) -> float:
    return max(0, box.x1 - box.x0) * max(0, box.y1 - box.y0)


def _intersection_area(a: BoundingBox, b: BoundingBox) -> float:
    return max(0, min(a.x1, b.x1) - max(a.x0, b.x0)) * max(0, min(a.y1, b.y1) - max(a.y0, b.y0))


def _overlaps(a: BoundingBox, b: BoundingBox, pad: float = 0) -> bool:
    return a.x0 < b.x1 + pad and a.x1 > b.x0 - pad and a.y0 < b.y1 + pad and a.y1 > b.y0 - pad


def _same_rectangle(a: BoundingBox, b: BoundingBox) -> bool:
    """Return true only with strong evidence that two paths draw one cell."""
    edge_delta = max(abs(a.x0 - b.x0), abs(a.y0 - b.y0), abs(a.x1 - b.x1), abs(a.y1 - b.y1))
    if edge_delta <= 1.5:
        return True
    smaller = min(_area(a), _area(b))
    coverage = _intersection_area(a, b) / smaller if smaller else 0
    # The inset rectangles in MAS files cover most of their outer cell.  A
    # slight overlap between adjacent cells is deliberately nowhere near this.
    return coverage >= .90 and min(_area(a), _area(b)) / max(_area(a), _area(b)) >= .45


def _deduplicate_fills(fills: list[FilledRectangle]) -> list[FilledRectangle]:
    unique: list[FilledRectangle] = []
    for fill in sorted(fills, key=lambda item: -_area(item.bbox)):
        if any(fill.rgb == existing.rgb and _same_rectangle(fill.bbox, existing.bbox) for existing in unique):
            continue
        unique.append(fill)
    return unique


def _join_label_lines(texts: list[TextSpan], x0: float, x1: float, y0: float, y1: float) -> str | None:
    selected = [
        text for text in texts
        if y0 <= (text.bbox.y0 + text.bbox.y1) / 2 <= y1
        and x0 <= (text.bbox.x0 + text.bbox.x1) / 2 <= x1
    ]
    if not selected:
        return None
    return " ".join(text.text for text in sorted(selected, key=lambda text: (text.bbox.y0, text.bbox.x0)))


@dataclass
class _Legend:
    swatches: list[FilledRectangle]
    meanings: dict[tuple[int, int, int], str]
    bbox: BoundingBox


def _bbox(fills: list[FilledRectangle]) -> BoundingBox:
    return BoundingBox(min(f.bbox.x0 for f in fills), min(f.bbox.y0 for f in fills),
                       max(f.bbox.x1 for f in fills), max(f.bbox.y1 for f in fills))


def _horizontal_legends(page: Page, fills: list[FilledRectangle]) -> list[_Legend]:
    legends: list[_Legend] = []
    used: set[int] = set()
    for seed in fills:
        if id(seed) in used:
            continue
        row = [f for f in fills if abs(f.bbox.y0 - seed.bbox.y0) <= 2 and abs(f.bbox.y1 - seed.bbox.y1) <= 2]
        row.sort(key=lambda f: f.bbox.x0)
        # Split the row where rectangles are not consecutive legend bands.
        runs: list[list[FilledRectangle]] = []
        for fill in row:
            if not runs or fill.bbox.x0 - runs[-1][-1].bbox.x1 > 3:
                runs.append([fill])
            else:
                runs[-1].append(fill)
        for run in runs:
            # A continuous scale needs at least three distinct bands. Runs of
            # repeated white/grey table shading are not legends.
            if len(run) < 3 or len({f.rgb for f in run}) < 3:
                continue
            band_height = max(f.bbox.y1 for f in run) - min(f.bbox.y0 for f in run)
            # Legend bands are a horizontal strip rather than table cells.
            if sum(f.bbox.x1 - f.bbox.x0 for f in run) / len(run) < band_height * 1.5:
                continue
            labels: dict[int, str] = {}
            for i, fill in enumerate(run):
                left = run[i - 1].bbox.x1 if i else fill.bbox.x0
                right = run[i + 1].bbox.x0 if i + 1 < len(run) else fill.bbox.x1
                label = _join_label_lines(page.texts, left, right, fill.bbox.y1, fill.bbox.y1 + 28)
                if label:
                    labels[i] = label
            if len(labels) < 2:
                continue
            meanings: dict[tuple[int, int, int], str] = {}
            for i, fill in enumerate(run):
                if i in labels:
                    meaning = labels[i]
                else:
                    before = max((j for j in labels if j < i), default=None)
                    after = min((j for j in labels if j > i), default=None)
                    interval = f" between {labels[before]} and {labels[after]}" if before is not None and after is not None else ""
                    meaning = UNRESOLVED + interval
                meanings.setdefault(fill.rgb, meaning)
            legends.append(_Legend(run, meanings, _bbox(run)))
            used.update(id(f) for f in run)
    return legends


def _vertical_legends(page: Page, fills: list[FilledRectangle], excluded: set[int]) -> list[_Legend]:
    pairs: list[tuple[FilledRectangle, TextSpan]] = []
    for fill in fills:
        if id(fill) in excluded:
            continue
        candidates = [t for t in page.texts if t.bbox.x0 >= fill.bbox.x1 - 1
                      and t.bbox.x0 - fill.bbox.x1 <= max(100, fill.bbox.x1 - fill.bbox.x0)
                      and t.bbox.y0 < fill.bbox.y1 + 3 and t.bbox.y1 > fill.bbox.y0 - 3]
        text = min(candidates, key=lambda t: t.bbox.x0, default=None)
        if text and len(text.text) >= 2 and not any(_overlaps(fill.bbox, t.bbox) for t in page.texts):
            pairs.append((fill, text))
    groups: list[list[tuple[FilledRectangle, TextSpan]]] = []
    for pair in pairs:
        group = next((g for g in groups if abs(g[0][0].bbox.x0 - pair[0].bbox.x0) <= 30
                      and abs(g[-1][0].bbox.y0 - pair[0].bbox.y0) <= page.height * .3), None)
        if group is None:
            groups.append([pair])
        else:
            group.append(pair)
    result = []
    for group in groups:
        if len({f.rgb for f, _ in group}) < 2 or len({t.text.casefold() for _, t in group}) < 2:
            continue
        meanings = {f.rgb: t.text for f, t in group}
        result.append(_Legend([f for f, _ in group], meanings, _bbox([f for f, _ in group])))
    return result


def _legends(page: Page) -> list[_Legend]:
    fills = _deduplicate_fills(page.fills)
    horizontal = _horizontal_legends(page, fills)
    excluded = {id(f) for legend in horizontal for f in legend.swatches}
    return horizontal + _vertical_legends(page, fills, excluded)


def _cluster(fills: list[FilledRectangle]) -> list[list[FilledRectangle]]:
    groups: list[list[FilledRectangle]] = []
    remaining = set(range(len(fills)))
    while remaining:
        todo, group = [remaining.pop()], []
        while todo:
            index = todo.pop(); current = fills[index]; group.append(current)
            close = [j for j in remaining if abs(fills[j].bbox.x0-current.bbox.x0) < 250 and abs(fills[j].bbox.y0-current.bbox.y0) < 120]
            for j in close: remaining.remove(j); todo.append(j)
        aligned = any(abs(a.bbox.x0-b.bbox.x0) <= 3 or abs(a.bbox.y0-b.bbox.y0) <= 3
                      for i, a in enumerate(group) for b in group[i+1:])
        if len(group) >= 2 and aligned: groups.append(group)
    return groups


def _ranks(values: list[float], tolerance: float = 3) -> dict[float, int]:
    centres: list[float] = []
    for value in sorted(values):
        if not centres or abs(value-centres[-1]) > tolerance: centres.append(value)
        else: centres[-1] = (centres[-1]+value)/2
    return {value: min(range(len(centres)), key=lambda i: abs(centres[i]-value)) for value in values}


def _legend_distance(table: BoundingBox, legend: _Legend) -> float:
    dx = max(0, legend.bbox.x0-table.x1, table.x0-legend.bbox.x1)
    dy = max(0, legend.bbox.y0-table.y1, table.y0-legend.bbox.y1)
    return math.hypot(dx, dy)


def _regular(values: list[float]) -> bool:
    # Ranks alone discard locations, so calculate clustered source positions.
    positions: list[float] = []
    for value in sorted(values):
        if not positions or abs(value - positions[-1]) > 3: positions.append(value)
    if len(positions) <= 2: return True
    gaps = [b-a for a, b in zip(positions, positions[1:])]
    return max(gaps) <= min(gaps) * 1.6


def extract_from_pages(pages: list[Page], *, color_tolerance: float = 18) -> DocumentColorCodeExtraction:
    """Extract facts, using zero-based physical row indexes and one-based data columns.

    Positions are ranked from the blank table structure before unsupported
    colours are filtered, so an omitted cell cannot renumber later facts.
    """
    result = DocumentColorCodeExtraction()
    for page in pages:
        legends = _legends(page)
        if not legends: continue
        swatches = [f for legend in legends for f in legend.swatches]
        structural = []
        for fill in _deduplicate_fills(page.fills):
            width, height = fill.bbox.x1-fill.bbox.x0, fill.bbox.y1-fill.bbox.y0
            # Absolute dimensions are deliberately modest; shape, alignment,
            # row-label, and legend evidence do the rejection work. Extremely
            # elongated marks are chart bars/lines rather than table cells.
            if width < 4 or height < 4 or max(width/height, height/width) > 9.5 or min(fill.rgb) >= 245: continue
            if any(_same_rectangle(fill.bbox, s.bbox) for s in swatches): continue
            if any(_overlaps(fill.bbox, text.bbox) for text in page.texts): continue
            structural.append(fill)
        for group in _cluster(structural):
            box = _bbox(group)
            xs, ys = _ranks([f.bbox.x0 for f in group]), _ranks([f.bbox.y0 for f in group])
            grid_slots = len(set(xs.values())) * len(set(ys.values()))
            # Scatter-plot markers may align by accident, but unlike a table
            # they occupy only a small fraction of their implied grid.
            if grid_slots and len(group) / grid_slots < .4: continue
            if not (_regular([f.bbox.x0 for f in group]) and _regular([f.bbox.y0 for f in group])): continue
            row_boxes: dict[int, BoundingBox] = {}
            for fill in group: row_boxes.setdefault(ys[fill.bbox.y0], fill.bbox)
            labelled_rows = sum(any(t.bbox.x1 <= box.x0+5 and t.bbox.x1 >= box.x0-250
                                    and t.bbox.y0 < row_box.y1+2 and t.bbox.y1 > row_box.y0-2
                                    for t in page.texts) for row_box in row_boxes.values())
            if labelled_rows / len(row_boxes) < .5: continue
            legend = min(legends, key=lambda item: _legend_distance(box, item))
            matches: dict[int, str] = {}
            for fill in group:
                distance, color = min((_distance(fill.rgb, rgb), rgb) for rgb in legend.meanings)
                # Some MAS editions use a lighter orange in the table than in
                # the printed swatch. Accept that producer variation only
                # when there is a unique nearest legend colour.
                ordered = sorted((_distance(fill.rgb, rgb), rgb) for rgb in legend.meanings)
                unambiguous = len(ordered) == 1 or ordered[1][0] - ordered[0][0] >= 12
                if distance <= color_tolerance or (distance <= 55 and unambiguous):
                    matches[id(fill)] = legend.meanings[color]
            if len(matches) < 2: continue
            facts = [ColorCodedFact(ys[f.bbox.y0], xs[f.bbox.x0]+1, _hex(f.rgb), matches[id(f)])
                     for f in sorted(group, key=lambda f: (f.bbox.y0, f.bbox.x0)) if id(f) in matches]
            title_candidates = [t for t in page.texts if t.bbox.y1 <= box.y0 and box.y0-t.bbox.y1 <= 80]
            title = max(title_candidates, key=lambda t: t.bbox.y1, default=None)
            entries = [LegendEntry(_hex(fill.rgb), legend.meanings[fill.rgb]) for fill in legend.swatches]
            result.items.append(ColorCodedTable(page.number, facts, title.text if title else None, box, entries))
    return result


def extract_color_coded_facts(path: str | Path, *, color_tolerance: float = 18) -> DocumentColorCodeExtraction:
    from .pdfplumber_backend import read_pages
    return extract_from_pages(read_pages(path), color_tolerance=color_tolerance)
