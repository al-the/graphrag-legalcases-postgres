from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

import fastapi
import httpx
from fastapi import Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from fastapi_app.auth.auth_config import current_active_user
from fastapi_app.auth.auth_models import User
from fastapi_app.db.document_models import Document, DocumentChunk, DocumentSource, OcrJob
from fastapi_app.dependencies import DBSession

logger = logging.getLogger(__name__)
router = fastapi.APIRouter(prefix="/api/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class FromUrlRequest(BaseModel):
    url: str
    doc_type: Optional[str] = None
    source_key: Optional[str] = None
    title: Optional[str] = None
    metadata: dict = {}


class DocumentResponse(BaseModel):
    id: str
    source_id: str
    doc_type: str
    title: str
    language: str
    source_url: Optional[str]
    ocr_status: str
    graphrag_status: str
    page_count: Optional[int]
    publication_date: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# URL domain → source_key mapping
# ---------------------------------------------------------------------------

URL_DOMAIN_TO_SOURCE: dict[str, str] = {
    "parlimen.gov.my":           "hansard",
    "bursa.com.my":              "bursa",
    "disclosure.bursa.com.my":   "bursa",
    "dosm.gov.my":               "dosm",
    "oecd.org":                  "oecd",
    "oecdilibrary.org":          "oecd",
    "fatf-gafi.org":             "fatf",
    "bnm.gov.my":                "bnm",
    "sc.com.my":                 "sc_malaysia",
}


def _detect_source_key(url: str) -> str:
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for domain, key in URL_DOMAIN_TO_SOURCE.items():
        if host.endswith(domain):
            return key
    return "web"


async def _get_or_create_source(session, source_key: str) -> DocumentSource:
    result = await session.execute(
        select(DocumentSource).where(DocumentSource.source_key == source_key)
    )
    src = result.scalars().first()
    if not src:
        src = DocumentSource(source_key=source_key, display_name=source_key.title(), source_type="manual_upload")
        session.add(src)
        await session.flush()
    return src


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/from-url", response_model=DocumentResponse)
async def add_document_from_url(
    body: FromUrlRequest,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    """Accept a PDF URL, download, deduplicate, and queue for OCR."""
    url = body.url.strip()

    # Compute hash from URL first (quick dedup); full hash after download
    existing = await session.execute(select(Document).where(Document.source_url == url))
    if doc := existing.scalars().first():
        return DocumentResponse(**doc.to_dict())

    # Download to temp file
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "pdf" not in content_type and "octet-stream" not in content_type:
                    raise HTTPException(400, f"URL does not point to a PDF (content-type: {content_type})")
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    async for chunk in resp.aiter_bytes(65536):
                        tmp.write(chunk)
                    pdf_path = Path(tmp.name)
    except httpx.HTTPError as e:
        raise HTTPException(400, f"Failed to download URL: {e}")

    # Dedup by file hash
    sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    existing_hash = await session.execute(select(Document).where(Document.file_hash == sha256))
    if dup := existing_hash.scalars().first():
        return DocumentResponse(**dup.to_dict())

    source_key = body.source_key or _detect_source_key(url)
    source = await _get_or_create_source(session, source_key)

    title = body.title or _extract_title_from_url(url)
    doc_type = body.doc_type or _guess_doc_type(source_key)

    # Determine storage path (local for workers; swap for blob in prod)
    storage_dir = Path(os.environ.get("PDF_STORAGE_DIR", "/tmp/mykg_pdfs"))
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_dir / f"{sha256}.pdf")
    pdf_path.rename(storage_path)

    doc = Document(
        source_id=source.id,
        doc_type=doc_type,
        title=title,
        source_url=url,
        storage_path=storage_path,
        file_hash=sha256,
        file_size_bytes=Path(storage_path).stat().st_size,
        metadata_=body.metadata,
        ocr_status="queued",
    )
    session.add(doc)
    await session.flush()

    ocr_engine = _select_engine(doc_type)
    job = OcrJob(document_id=doc.id, ocr_engine=ocr_engine, status="pending")
    session.add(job)
    await session.commit()

    # Dispatch to Celery
    from fastapi_app.workers.ocr_tasks import process_ocr_job
    process_ocr_job.apply_async(args=[str(job.id)], queue="default")

    return DocumentResponse(**doc.to_dict())


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    session: DBSession,
    user: User = Depends(current_active_user),
    file: UploadFile = File(...),
    doc_type: str = Query("policy_paper"),
    source_key: str = Query("manual"),
    title: Optional[str] = Query(None),
):
    """Upload a local PDF file for OCR ingestion."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    contents = await file.read()
    sha256 = hashlib.sha256(contents).hexdigest()

    existing = await session.execute(select(Document).where(Document.file_hash == sha256))
    if dup := existing.scalars().first():
        return DocumentResponse(**dup.to_dict())

    storage_dir = Path(os.environ.get("PDF_STORAGE_DIR", "/tmp/mykg_pdfs"))
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_dir / f"{sha256}.pdf")
    Path(storage_path).write_bytes(contents)

    source = await _get_or_create_source(session, source_key)
    doc = Document(
        source_id=source.id,
        doc_type=doc_type,
        title=title or file.filename,
        storage_path=storage_path,
        file_hash=sha256,
        file_size_bytes=len(contents),
        ocr_status="queued",
    )
    session.add(doc)
    await session.flush()

    job = OcrJob(document_id=doc.id, ocr_engine=_select_engine(doc_type), status="pending")
    session.add(job)
    await session.commit()

    from fastapi_app.workers.ocr_tasks import process_ocr_job
    process_ocr_job.apply_async(args=[str(job.id)], queue="high")

    return DocumentResponse(**doc.to_dict())


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    session: DBSession,
    user: User = Depends(current_active_user),
    source_key: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    ocr_status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    q = select(Document)
    if source_key:
        src = await session.execute(select(DocumentSource).where(DocumentSource.source_key == source_key))
        s = src.scalars().first()
        if s:
            q = q.where(Document.source_id == s.id)
    if doc_type:
        q = q.where(Document.doc_type == doc_type)
    if ocr_status:
        q = q.where(Document.ocr_status == ocr_status)
    q = q.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    rows = await session.execute(q)
    return [DocumentResponse(**d.to_dict()) for d in rows.scalars().all()]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentResponse(**doc.to_dict())


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: UUID,
    session: DBSession,
    user: User = Depends(current_active_user),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    rows = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .limit(limit).offset(offset)
    )
    return [c.to_dict() for c in rows.scalars().all()]


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    session: DBSession,
    user: User = Depends(current_active_user),
    stage: str = Query("ocr", description="'ocr' or 'graphrag'"),
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Document not found")

    if stage == "ocr":
        job = OcrJob(document_id=doc.id, ocr_engine=_select_engine(doc.doc_type))
        session.add(job)
        doc.ocr_status = "queued"
        await session.commit()
        from fastapi_app.workers.ocr_tasks import process_ocr_job
        process_ocr_job.apply_async(args=[str(job.id)], queue="high")
    elif stage == "graphrag":
        doc.graphrag_status = "queued"
        await session.commit()
    return {"status": "requeued", "stage": stage}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_engine(doc_type: str) -> str:
    from fastapi_app.ocr.ocr_router import select_engine
    return select_engine(doc_type)


def _extract_title_from_url(url: str) -> str:
    from urllib.parse import urlparse
    name = Path(urlparse(url).path).stem
    return name.replace("-", " ").replace("_", " ").title() or url


def _guess_doc_type(source_key: str) -> str:
    mapping = {
        "hansard": "hansard_debate",
        "bursa": "annual_report",
        "dosm": "dosm_publication",
        "oecd": "policy_paper",
        "fatf": "policy_paper",
        "bnm": "regulation",
        "sc_malaysia": "regulation",
    }
    return mapping.get(source_key, "policy_paper")
