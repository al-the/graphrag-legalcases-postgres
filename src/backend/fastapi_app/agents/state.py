from __future__ import annotations

from datetime import datetime
from typing import Optional, TypedDict


class WorkflowState(TypedDict):
    run_id: str
    source_keys: list[str]
    since_date: Optional[datetime]
    discovered_docs: list[str]       # document IDs
    ocr_completed: list[str]
    ocr_failed: list[str]
    graphrag_run_id: Optional[str]
    validation_passed: bool
    errors: list[str]
    status: str                       # 'running' | 'done' | 'failed' | 'partial'
