from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi_app.ocr.models import OCRResult

logger = logging.getLogger(__name__)


async def run_marker(document_id: str, pdf_path: Path, langs: list[str] | None = None) -> OCRResult:
    """Convert a PDF to markdown using marker-pdf."""
    import subprocess
    import sys

    lang_flag = ",".join(langs or ["en", "ms"])

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            sys.executable, "-m", "marker_single",
            str(pdf_path),
            "--output_dir", tmpdir,
            "--langs", lang_flag,
        ]
        logger.info("Running marker-pdf: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            raise RuntimeError(f"marker-pdf failed: {result.stderr[:500]}")

        # marker outputs a .md file named after the PDF stem
        md_files = list(Path(tmpdir).rglob("*.md"))
        if not md_files:
            raise RuntimeError("marker-pdf produced no markdown output")

        markdown_text = md_files[0].read_text(encoding="utf-8")

    word_count = len(markdown_text.split())
    page_count = max(1, markdown_text.count("\x0c") + 1)

    from fastapi_app.ocr.language_detector import detect_bilingual
    detected_language = detect_bilingual(markdown_text)

    return OCRResult(
        document_id=document_id,
        markdown_text=markdown_text,
        page_count=page_count,
        word_count=word_count,
        detected_language=detected_language,
        output_path="",  # caller saves to blob
    )
