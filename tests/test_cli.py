import json
from pathlib import Path

from typer.testing import CliRunner

import cli.__main__ as cli_module
from pdf_color_facts import ColorCodeRunner


cli = CliRunner()


def test_single_file_mode_reports_output(monkeypatch, tmp_path):
    pdf = tmp_path / "report.PDF"
    pdf.touch()
    calls = []

    class FakeRunner:
        def __init__(self, path):
            self.filepath = Path(path)
            self.output_path = self.filepath.with_name(f"{self.filepath.stem}_color_code.json")

        def run(self):
            calls.append(self.filepath)

    monkeypatch.setattr(cli_module, "ColorCodeRunner", FakeRunner)
    result = cli.invoke(cli_module.app, ["--fpath", str(pdf)])

    assert result.exit_code == 0
    assert calls == [pdf]
    assert f"Generated {tmp_path / 'report_color_code.json'}" in result.stdout


def test_directory_mode_is_case_insensitive_and_deterministic(monkeypatch, tmp_path):
    for name in ["z.pdf", "A.PDF", "ignore.txt", "b.PdF"]:
        (tmp_path / name).touch()
    calls = []

    class FakeRunner:
        def __init__(self, path):
            self.filepath = Path(path)
            self.output_path = self.filepath.with_suffix(".json")

        def run(self):
            calls.append(self.filepath.name)

    monkeypatch.setattr(cli_module, "ColorCodeRunner", FakeRunner)
    result = cli.invoke(cli_module.app, ["--dir", str(tmp_path)])

    assert result.exit_code == 0
    assert calls == ["A.PDF", "b.PdF", "z.pdf"]


def test_rejects_both_or_neither_input_mode(tmp_path):
    pdf = tmp_path / "one.pdf"
    pdf.touch()

    neither = cli.invoke(cli_module.app, [])
    both = cli.invoke(cli_module.app, ["--fpath", str(pdf), "--dir", str(tmp_path)])

    assert neither.exit_code != 0
    assert both.exit_code != 0
    assert "exactly one of --fpath or --dir is required" in neither.output
    assert "exactly one of --fpath or --dir is required" in both.output


def test_empty_directory_is_an_error(tmp_path):
    result = cli.invoke(cli_module.app, ["--dir", str(tmp_path)])

    assert result.exit_code != 0
    assert "directory contains no PDF files" in result.output


def test_directory_continues_after_failure_and_exits_nonzero(monkeypatch, tmp_path):
    for name in ["a.pdf", "b.pdf", "c.pdf"]:
        (tmp_path / name).touch()
    calls = []

    class FakeRunner:
        def __init__(self, path):
            self.filepath = Path(path)
            self.output_path = self.filepath.with_suffix(".json")

        def run(self):
            calls.append(self.filepath.name)
            if self.filepath.name == "b.pdf":
                raise RuntimeError("broken PDF")

    monkeypatch.setattr(cli_module, "ColorCodeRunner", FakeRunner)
    result = cli.invoke(cli_module.app, ["--dir", str(tmp_path)])

    assert result.exit_code == 1
    assert calls == ["a.pdf", "b.pdf", "c.pdf"]
    assert "Failed" in result.output and "broken PDF" in result.output
    assert "1 of 3 PDF(s) failed" in result.output


def test_file_mode_exercises_runner_and_cli(monkeypatch, tmp_path):
    pdf = tmp_path / "generated.pdf"
    teal = (0, 90 / 255, 90 / 255)
    red = (190 / 255, 30 / 255, 30 / 255)
    pdf.touch()
    from pdf_color_facts.primitives import FilledRectangle, Page, TextSpan
    from pdf_color_facts import BoundingBox

    def box(x, y, w=20, h=12):
        return BoundingBox(x, y, x + w, y + h)

    page = Page(1, 600, 800,
        texts=[TextSpan("Risk dashboard", box(40, 80)), TextSpan("Metric A", box(40, 100)),
               TextSpan("Metric B", box(40, 120)), TextSpan("Lower vulnerability", box(430, 600, 110)),
               TextSpan("Higher vulnerability", box(430, 620, 110))],
        fills=[FilledRectangle(box(120, 100), tuple(round(x * 255) for x in teal)),
               FilledRectangle(box(160, 100), tuple(round(x * 255) for x in red)),
               FilledRectangle(box(120, 120), tuple(round(x * 255) for x in red)),
               FilledRectangle(box(160, 120), tuple(round(x * 255) for x in teal)),
               FilledRectangle(box(400, 600), tuple(round(x * 255) for x in teal)),
               FilledRectangle(box(400, 620), tuple(round(x * 255) for x in red))])
    monkeypatch.setattr("pdf_color_facts.pdfplumber_backend.read_pages", lambda path: [page])

    result = cli.invoke(cli_module.app, ["--fpath", str(pdf)])

    assert result.exit_code == 0, result.output
    payload = json.loads(ColorCodeRunner(pdf).output_path.read_text(encoding="utf-8"))
    assert len(payload["items"]) == 1
    assert len(payload["items"][0]["facts"]) == 4
    assert payload["items"][0]["bbox"] == {"x0": 120.0, "y0": 100.0, "x1": 180.0, "y1": 132.0}
