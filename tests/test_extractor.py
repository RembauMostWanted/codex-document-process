from pdf_color_facts import BoundingBox, extract_from_pages
from pdf_color_facts.extractor import _deduplicate_fills
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


def test_deduplicates_nested_cell_rectangles_and_rejects_chart_bars():
    teal, red = (0, 90, 90), (190, 30, 30)
    page = Page(1, 600, 800,
        texts=[TextSpan("A", box(40, 100)), TextSpan("B", box(40, 120)),
               TextSpan("low", box(430, 600)), TextSpan("high", box(430, 620))],
        fills=[FilledRectangle(box(120, 100, 40), teal),
               FilledRectangle(box(124, 102, 32, 8), teal),
               FilledRectangle(box(120, 120, 40), red),
               FilledRectangle(box(124, 122, 32, 8), red),
               # Aligned chart bars share legend colours but are not cells.
               FilledRectangle(box(250, 100, 5, 50), teal),
               FilledRectangle(box(260, 100, 5, 70), red),
               FilledRectangle(box(400, 600), teal),
               FilledRectangle(box(400, 620), red)])

    result = extract_from_pages([page])

    assert len(result.items) == 1
    assert [(fact.row_idx, fact.col_idx) for fact in result.items[0].facts] == [
        (0, 1), (1, 1)
    ]


def test_rejects_monochrome_table_shading_mistaken_for_a_legend():
    gray = (220, 220, 220)
    page = Page(1, 600, 800,
        texts=[TextSpan("Row A", box(40, 100)), TextSpan("Row B", box(40, 120)),
               TextSpan("Full", box(430, 600)), TextSpan("Partial", box(430, 620))],
        fills=[FilledRectangle(box(120, 100, 40), gray),
               FilledRectangle(box(120, 120, 40), gray),
               FilledRectangle(box(400, 600), gray),
               FilledRectangle(box(400, 620), gray)])

    assert extract_from_pages([page]).items == []


def test_horizontal_five_band_legend_preserves_exact_and_unresolved_meanings():
    colours = [(0, 128, 128), (71, 192, 159), (217, 225, 242),
               (239, 131, 105), (218, 48, 49)]
    legend = [FilledRectangle(box(150 + i * 60, 600, 60, 15), colour)
              for i, colour in enumerate(colours)]
    page = Page(9, 600, 800,
        texts=[TextSpan("FVI level quintiles", box(255, 580, 100, 10)),
               TextSpan("Lower", box(165, 616, 30, 8)),
               TextSpan("vulnerability", box(155, 626, 50, 8)),
               TextSpan("Average", box(280, 616, 40, 8)),
               TextSpan("vulnerability", box(275, 626, 50, 8)),
               TextSpan("Higher", box(405, 616, 35, 8)),
               TextSpan("vulnerability", box(395, 626, 50, 8)),
               TextSpan("Metric A", box(40, 100, 60)), TextSpan("Metric B", box(40, 120, 60))],
        fills=[FilledRectangle(box(120, 100, 60), colours[1]),
               FilledRectangle(box(120, 120, 60), colours[2]), *legend])

    table = extract_from_pages([page]).items[0]
    assert [entry.interpretation for entry in table.legend] == [
        "Lower vulnerability",
        "Unresolved between Lower vulnerability and Average vulnerability",
        "Average vulnerability",
        "Unresolved between Average vulnerability and Higher vulnerability",
        "Higher vulnerability",
    ]
    assert [fact.interpretation for fact in table.facts] == [
        "Unresolved between Lower vulnerability and Average vulnerability",
        "Average vulnerability",
    ]
    assert all("FVI level quintiles" not in entry.interpretation for entry in table.legend)


def test_2020_household_layout_recovers_orange_cell_and_coordinates():
    colours = [(0, 128, 128), (71, 192, 159), (217, 225, 242),
               (244, 176, 131), (218, 48, 49)]
    page = Page(9, 595, 842,
        texts=[TextSpan("Overall Corporate FVI", box(99, 590, 95, 10)),
               TextSpan("Overall Household FVI", box(99, 604, 98, 10)),
               TextSpan("Overall Banking FVI", box(99, 618, 86, 10)),
               TextSpan("Decreased", box(221, 701, 33, 8)), TextSpan("significantly", box(221, 711, 38, 8)),
               TextSpan("Broadly", box(286, 701, 24, 8)), TextSpan("Unchanged", box(280, 711, 36, 8)),
               TextSpan("Increased", box(341, 701, 30, 8)), TextSpan("significantly", box(337, 711, 38, 8))],
        fills=[FilledRectangle(box(384, 587, 120, 13), colours[2]),
               FilledRectangle(box(384, 601, 120, 13), colours[3]),
               FilledRectangle(box(384, 615, 120, 13), colours[2]),
               *[FilledRectangle(box(x, 693, w, 7), c) for x, w, c in
                 zip((215, 249, 281, 314, 345), (34, 32, 33, 31, 35), colours)]])

    facts = extract_from_pages([page]).items[0].facts
    assert [(f.row_idx, f.col_idx, f.color_code, f.interpretation) for f in facts] == [
        (0, 1, "#D9E1F2", "Broadly Unchanged"),
        (1, 1, "#F4B083", "Unresolved between Broadly Unchanged and Increased significantly"),
        (2, 1, "#D9E1F2", "Broadly Unchanged"),
    ]


def test_coordinates_are_ranked_before_unsupported_cells_are_omitted():
    teal, red, unsupported = (0, 90, 90), (190, 30, 30), (80, 80, 200)
    page = Page(1, 600, 800,
        texts=[TextSpan("row 0", box(40, 100)), TextSpan("row 1", box(40, 120)),
               TextSpan("row 2", box(40, 140)), TextSpan("low", box(430, 600)),
               TextSpan("high", box(430, 620))],
        fills=[FilledRectangle(box(120, 100), unsupported), FilledRectangle(box(160, 100), teal),
               FilledRectangle(box(120, 120), teal), FilledRectangle(box(160, 120), unsupported),
               FilledRectangle(box(120, 140), red), FilledRectangle(box(160, 140), teal),
               FilledRectangle(box(400, 600), teal), FilledRectangle(box(400, 620), red)])
    facts = extract_from_pages([page]).items[0].facts
    assert [(f.row_idx, f.col_idx) for f in facts] == [(0, 2), (1, 1), (2, 1), (2, 2)]


def test_valid_monochrome_table_is_not_rejected_when_legend_is_multicolour():
    teal, red = (0, 90, 90), (190, 30, 30)
    page = Page(1, 600, 800,
        texts=[TextSpan(f"row {i}", box(40, 100 + i * 20)) for i in range(3)]
              + [TextSpan("low", box(430, 600)), TextSpan("high", box(430, 620))],
        fills=[FilledRectangle(box(120, 100 + i * 20), teal) for i in range(3)]
              + [FilledRectangle(box(400, 600), teal), FilledRectangle(box(400, 620), red)])
    table = extract_from_pages([page]).items[0]
    assert [(f.row_idx, f.interpretation) for f in table.facts] == [(0, "low"), (1, "low"), (2, "low")]


def test_rectangle_deduplication_requires_near_identity_or_containment():
    teal = (0, 90, 90)
    exact = FilledRectangle(box(100, 100, 40, 20), teal)
    nested = FilledRectangle(box(104, 102, 32, 16), teal)
    # Twenty-five per cent overlap is not evidence that this is the same cell.
    neighbour = FilledRectangle(box(130, 100, 40, 20), teal)
    deduplicated = _deduplicate_fills([exact, exact, nested, neighbour])
    assert deduplicated == [exact, neighbour]
