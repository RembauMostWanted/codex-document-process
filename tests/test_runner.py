import json

from pdf_color_facts import (
    BoundingBox,
    ColorCodedFact,
    ColorCodedTable,
    ColorCodeRunner,
    DocumentColorCodeExtraction,
    LegendEntry,
)


def test_runner_serializes_complete_result_beside_pdf(monkeypatch, tmp_path):
    pdf = tmp_path / "annual.report.pdf"
    pdf.write_bytes(b"not read because extraction is stubbed")
    expected = DocumentColorCodeExtraction(
        items=[
            ColorCodedTable(
                page_number=2,
                facts=[ColorCodedFact(1, 3, "#005A5A", "Lower vulnerability")],
                title="Risk table",
                bbox=BoundingBox(10, 20, 30, 40),
                legend=[LegendEntry("#005A5A", "Lower vulnerability")],
            )
        ]
    )
    monkeypatch.setattr("pdf_color_facts.runner.extract_color_coded_facts", lambda path: expected)

    runner = ColorCodeRunner(pdf)
    actual = runner.run()

    assert actual is expected
    assert runner.output_path == tmp_path / "annual.report_color_code.json"
    assert json.loads(runner.output_path.read_text(encoding="utf-8")) == {
        "items": [{
            "page_number": 2,
            "facts": [{"row_idx": 1, "col_idx": 3, "color_code": "#005A5A", "interpretation": "Lower vulnerability"}],
            "title": "Risk table",
            "bbox": {"x0": 10, "y0": 20, "x1": 30, "y1": 40},
            "legend": [{"color_code": "#005A5A", "interpretation": "Lower vulnerability"}],
        }]
    }
    assert runner.output_path.read_text(encoding="utf-8").startswith('{\n  "items"')


def test_runner_writes_empty_extraction_as_items_array(monkeypatch, tmp_path):
    pdf = tmp_path / "empty.pdf"
    pdf.touch()
    monkeypatch.setattr(
        "pdf_color_facts.runner.extract_color_coded_facts",
        lambda path: DocumentColorCodeExtraction(),
    )

    ColorCodeRunner(pdf).run()

    assert json.loads((tmp_path / "empty_color_code.json").read_text()) == {"items": []}


def test_failed_extraction_does_not_replace_existing_output(monkeypatch, tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.touch()
    output = tmp_path / "report_color_code.json"
    output.write_text("existing", encoding="utf-8")

    def fail(path):
        raise RuntimeError("backend failed")

    monkeypatch.setattr("pdf_color_facts.runner.extract_color_coded_facts", fail)

    try:
        ColorCodeRunner(pdf).run()
    except RuntimeError:
        pass
    else:
        raise AssertionError("runner should propagate extraction errors")
    assert output.read_text(encoding="utf-8") == "existing"
