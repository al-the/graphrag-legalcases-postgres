from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PageMetadata:
    page_number: int
    char_start: int
    char_end: int


@dataclass
class ChunkData:
    chunk_index: int
    text: str
    section_title: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    language: str
    n_tokens: int
    metadata: dict = field(default_factory=dict)


@dataclass
class OCRResult:
    document_id: str
    markdown_text: str
    page_count: int
    word_count: int
    detected_language: str
    output_path: str
    page_map: list[PageMetadata] = field(default_factory=list)
    chunks: list[ChunkData] = field(default_factory=list)
