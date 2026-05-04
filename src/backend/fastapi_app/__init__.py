"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Malaysian Knowledge Graph RAG", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Existing routes
    from fastapi_app.routes.api_routes import router as api_router
    from fastapi_app.routes.frontend_routes import router as frontend_router

    # New routes
    from fastapi_app.routes.auth_routes import router as auth_router
    from fastapi_app.routes.document_routes import router as document_router
    from fastapi_app.routes.graph_routes import router as graph_router
    from fastapi_app.routes.workflow_routes import router as workflow_router

    app.include_router(auth_router)
    app.include_router(document_router)
    app.include_router(graph_router)
    app.include_router(workflow_router)
    app.include_router(api_router)
    app.include_router(frontend_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
