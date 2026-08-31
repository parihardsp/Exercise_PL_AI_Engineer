"""
FastAPI Application Setup for Portfolio Analytics Agent.

Includes:
  - CORS middleware for frontend integrations (Streamlit / React / Vue)
  - Process time tracking middleware
  - OpenAPI metadata and Swagger UI documentation
"""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router_tools, router_health
from utils.logger import logger


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    app = FastAPI(
        title="Portfolio Analytics AI Agent API",
        description=(
            "Production-ready REST API for the Portfolio Analytics Agent. "
            "Supports natural language Text-to-SQL queries, sector exposure calculations, "
            "hybrid multi-step workflows, and concurrent execution."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. CORS Middleware (allows web dashboards & Streamlit to call the API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Timing Middleware: Appends X-Process-Time-Ms header to every response
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        return response

    # 3. Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"[API] Unhandled error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred.", "error": str(exc)},
        )

    # 4. Include Endpoints Router
    app.include_router(router_tools)
    app.include_router(router_health)

    # 5. Root Welcome Route
    @app.get("/", tags=["General"], summary="Root endpoint")
    async def root():
        return {
            "service": "Portfolio Analytics AI Agent API",
            "version": "1.0.0",
            "status": "online",
            "documentation": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
