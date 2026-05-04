from __future__ import annotations

import re
from typing import Optional

import tiktoken

from fastapi_app.ocr.language_detector import detect_language
from fastapi_app.ocr.models import ChunkData

CHUNK_TARGET_TOKENS = 1200
CHUNK_OVERLAP_TOKENS = 200
HEADING_RE = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)

_enc = tiktoken.get_encoding("o200k_base")


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def _split_by_tokens(text: str, target: int, overlap: int) -> list[str]:
    tokens = _enc.encode(text)
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + target, len(tokens))
        chunks.append(_enc.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start = end - overlap
    return chunks


def build_chunks(markdown_text: str, page_map: Optional[dict[int, int]] = None) -> list[ChunkData]:
    """Split OCR markdown into overlapping chunks, respecting heading boundaries."""
    sections = _split_by_headings(markdown_text)
    chunks: list[ChunkData] = []
    idx = 0

    for section_title, section_text in sections:
        token_count = _count_tokens(section_text)
        if token_count <= CHUNK_TARGET_TOKENS:
            sub_texts = [section_text]
        else:
            sub_texts = _split_by_tokens(section_text, CHUNK_TARGET_TOKENS, CHUNK_OVERLAP_TOKENS)

        for sub in sub_texts:
            if not sub.strip():
                continue
            lang = detect_language(sub)
            page_start, page_end = _resolve_pages(sub, page_map)
            chunks.append(ChunkData(
                chunk_index=idx,
                text=sub.strip(),
                section_title=section_title,
                page_start=page_start,
                page_end=page_end,
                language=lang,
                n_tokens=_count_tokens(sub),
            ))
            idx += 1

    return chunks


def _split_by_headings(text: str) -> list[tuple[Optional[str], str]]:
    """Return list of (heading_title, section_text) tuples."""
    parts: list[tuple[Optional[str], str]] = []
    last_pos = 0
    current_title: Optional[str] = None

    for m in HEADING_RE.finditer(text):
        section_text = text[last_pos:m.start()].strip()
        if section_text:
            parts.append((current_title, section_text))
        current_title = m.group(2).strip()
        last_pos = m.end()

    tail = text[last_pos:].strip()
    if tail:
        parts.append((current_title, tail))

    return parts if parts else [(None, text)]


def _resolve_pages(text: str, page_map: Optional[dict[int, int]]) -> tuple[Optional[int], Optional[int]]:
    if not page_map:
        return None, None
    # page_map: char_offset → page_number; find min/max page for text chars
    return None, None  # simplified; real impl would use char offsets
