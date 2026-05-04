from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery(
    "mykg",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "fastapi_app.workers.ocr_tasks",
        "fastapi_app.workers.graphrag_tasks",
        "fastapi_app.workers.workflow_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kuala_Lumpur",
    enable_utc=True,
    task_routes={
        "fastapi_app.workers.ocr_tasks.*": {"queue": "default"},
        "fastapi_app.workers.graphrag_tasks.*": {"queue": "low"},
        "fastapi_app.workers.workflow_tasks.*": {"queue": "low"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
