"""Run the PDF colour extraction command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pdf_color_facts import ColorCodeRunner

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Extract colour-coded facts from PDF documents.",
)


def _pdfs(directory: Path) -> list[Path]:
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.casefold() == ".pdf"),
        key=lambda path: (path.name.casefold(), path.name),
    )


@app.callback(invoke_without_command=True)
def main(
    fpath: Annotated[Path | None, typer.Option("--fpath", help="Process one PDF file.")] = None,
    directory: Annotated[Path | None, typer.Option("--dir", help="Process immediate PDF files in a directory.")] = None,
) -> None:
    """Extract colour-coded facts and write JSON beside each source PDF."""
    if (fpath is None) == (directory is None):
        raise typer.BadParameter("exactly one of --fpath or --dir is required")

    if fpath is not None:
        if not fpath.is_file() or fpath.suffix.casefold() != ".pdf":
            raise typer.BadParameter("--fpath must identify an existing PDF file", param_hint="--fpath")
        runner = ColorCodeRunner(fpath)
        try:
            runner.run()
        except Exception as error:
            typer.echo(f"Failed {fpath}: {error}", err=True)
            raise typer.Exit(code=1) from error
        typer.echo(f"Generated {runner.output_path}")
        return

    assert directory is not None
    if not directory.is_dir():
        raise typer.BadParameter("--dir must identify an existing directory", param_hint="--dir")
    pdfs = _pdfs(directory)
    if not pdfs:
        raise typer.BadParameter("directory contains no PDF files", param_hint="--dir")

    failures: list[tuple[Path, Exception]] = []
    for pdf in pdfs:
        runner = ColorCodeRunner(pdf)
        try:
            runner.run()
        except Exception as error:
            failures.append((pdf, error))
            typer.echo(f"Failed {pdf}: {error}", err=True)
        else:
            typer.echo(f"Generated {runner.output_path}")

    if failures:
        typer.echo(f"{len(failures)} of {len(pdfs)} PDF(s) failed.", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
