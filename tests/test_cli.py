import json
from pathlib import Path

import fitz
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


def test_real_pdf_exercises_backend_runner_and_cli(tmp_path):
    pdf = tmp_path / "generated.pdf"
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    teal = (0, 90 / 255, 90 / 255)
    red = (190 / 255, 30 / 255, 30 / 255)
    page.insert_text((40, 95), "Risk dashboard")
    page.insert_text((40, 113), "Metric A")
    page.insert_text((40, 133), "Metric B")
    for rect, colour in [
        (fitz.Rect(120, 100, 140, 112), teal), (fitz.Rect(160, 100, 180, 112), red),
        (fitz.Rect(120, 120, 140, 132), red), (fitz.Rect(160, 120, 180, 132), teal),
        (fitz.Rect(400, 600, 420, 612), teal), (fitz.Rect(400, 620, 420, 632), red),
    ]:
        page.draw_rect(rect, fill=colour, color=None)
    page.insert_text((430, 610), "Lower vulnerability")
    page.insert_text((430, 630), "Higher vulnerability")
    document.save(pdf)
    document.close()

    result = cli.invoke(cli_module.app, ["--fpath", str(pdf)])

    assert result.exit_code == 0, result.output
    payload = json.loads(ColorCodeRunner(pdf).output_path.read_text(encoding="utf-8"))
    assert len(payload["items"]) == 1
    assert len(payload["items"][0]["facts"]) == 4
    assert payload["items"][0]["bbox"] == {"x0": 120.0, "y0": 100.0, "x1": 180.0, "y1": 132.0}
