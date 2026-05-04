from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class DocumentBase(DeclarativeBase):
    pass


class DocumentSource(DocumentBase):
    __tablename__ = "document_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list[Document]] = relationship("Document", back_populates="source")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "source_key": self.source_key,
            "display_name": self.display_name,
            "source_type": self.source_type,
            "base_url": self.base_url,
            "is_active": self.is_active,
            "last_crawled_at": self.last_crawled_at.isoformat() if self.last_crawled_at else None,
            "created_at": self.created_at.isoformat(),
        }


class Document(DocumentBase):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_sources.id"), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_ms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(Text, default="en")
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", MutableDict.as_mutable(JSONB), default=dict)
    ocr_status: Mapped[str] = mapped_column(Text, default="pending")
    graphrag_status: Mapped[str] = mapped_column(Text, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    source: Mapped[DocumentSource] = relationship("DocumentSource", back_populates="documents")
    ocr_jobs: Mapped[list[OcrJob]] = relationship("OcrJob", back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list[DocumentChunk]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self, include_chunks: bool = False) -> dict:
        d = {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "external_id": self.external_id,
            "doc_type": self.doc_type,
            "title": self.title,
            "title_ms": self.title_ms,
            "language": self.language,
            "source_url": self.source_url,
            "storage_path": self.storage_path,
            "file_hash": self.file_hash,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "metadata": self.metadata_,
            "ocr_status": self.ocr_status,
            "graphrag_status": self.graphrag_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        return d


class OcrJob(DocumentBase):
    __tablename__ = "ocr_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending")
    ocr_engine: Mapped[str] = mapped_column(Text, default="marker-pdf")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detected_language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document: Mapped[Document] = relationship("Document", back_populates="ocr_jobs")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "status": self.status,
            "ocr_engine": self.ocr_engine,
            "attempt_count": self.attempt_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "detected_language": self.detected_language,
        }


class DocumentChunk(DocumentBase):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, default="en")
    n_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_vector: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)
    graphrag_text_unit_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", MutableDict.as_mutable(JSONB), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    def to_dict(self, include_vector: bool = False) -> dict:
        d = {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "section_title": self.section_title,
            "text": self.text,
            "language": self.language,
            "n_tokens": self.n_tokens,
            "graphrag_text_unit_id": self.graphrag_text_unit_id,
        }
        if include_vector:
            d["chunk_vector"] = list(self.chunk_vector) if self.chunk_vector is not None else None
        return d


class GraphragRun(DocumentBase):
    __tablename__ = "graphrag_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(Text, default="full")
    status: Mapped[str] = mapped_column(Text, default="pending")
    document_ids: Mapped[Optional[list]] = mapped_column(MutableList.as_mutable(ARRAY(UUID(as_uuid=True))), nullable=True)
    entity_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relationship_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    community_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_snapshot: Mapped[Optional[dict]] = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "run_type": self.run_type,
            "status": self.status,
            "document_ids": [str(d) for d in self.document_ids] if self.document_ids else [],
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "community_count": self.community_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
