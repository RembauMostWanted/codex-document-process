"""Reusable document runner and JSON output support."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .extractor import extract_color_coded_facts
from .models import DocumentColorCodeExtraction


class ColorCodeRunner:
    """Extract colour-coded facts from one PDF and atomically write JSON."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

    @property
    def output_path(self) -> Path:
        """Path of the JSON document produced by :meth:`run`."""
        return self.filepath.with_name(f"{self.filepath.stem}_color_code.json")

    def run(self) -> DocumentColorCodeExtraction:
        """Extract this PDF, write its complete result, and return the result.

        JSON is rendered in memory before a temporary file is created. The
        final ``os.replace`` is atomic when the source and destination are on
        the same filesystem, so a failed run cannot leave partial output.
        """
        result = extract_color_coded_facts(self.filepath)
        payload = json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n"

        output_path = self.output_path
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, output_path)
        except BaseException:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

        return result
