from pdf_color_facts import BoundingBox, extract_from_pages
from pdf_color_facts.primitives import FilledRectangle, Page, TextSpan


def box(x, y, w=20, h=12):
    return BoundingBox(x, y, x + w, y + h)


def test_extracts_blank_aligned_cells_using_multi_entry_legend():
    teal, red = (0, 90, 90), (190, 30, 30)
    page = Page(3, 600, 800,
        texts=[TextSpan("Risk dashboard", box(40, 40, 100)), TextSpan("Metric A", box(40, 103, 45)),
               TextSpan("Metric B", box(40, 123, 45)), TextSpan("Lower vulnerability", box(430, 600, 110)),
               TextSpan("Higher vulnerability", box(430, 620, 110))],
        fills=[FilledRectangle(box(120, 100), teal), FilledRectangle(box(160, 100), red),
               FilledRectangle(box(120, 120), red), FilledRectangle(box(160, 120), teal),
               FilledRectangle(box(400, 600), teal), FilledRectangle(box(400, 620), red)])
    result = extract_from_pages([page])
    assert len(result.items) == 1
    assert [(f.row_idx, f.col_idx, f.interpretation) for f in result.items[0].facts] == [
        (0, 1, "Lower vulnerability"), (0, 2, "Higher vulnerability"),
        (1, 1, "Higher vulnerability"), (1, 2, "Lower vulnerability")]
    assert result.items[0].page_number == 3


def test_does_not_promote_blank_fill_without_legend_or_table_evidence():
    page = Page(1, 600, 800, texts=[TextSpan("ordinary blank", box(40, 100, 60))],
                fills=[FilledRectangle(box(120, 100), (0, 90, 90))])
    assert extract_from_pages([page]).items == []


def test_rejects_cell_containing_text():
    teal, red = (0, 90, 90), (190, 30, 30)
    page = Page(1, 600, 800,
        texts=[TextSpan("A", box(40, 100)), TextSpan("not blank", box(121, 101, 15, 8)),
               TextSpan("low", box(430, 600)), TextSpan("high", box(430, 620))],
        fills=[FilledRectangle(box(120, 100), teal), FilledRectangle(box(120, 120), red),
               FilledRectangle(box(400, 600), teal), FilledRectangle(box(400, 620), red)])
    assert extract_from_pages([page]).items == []
