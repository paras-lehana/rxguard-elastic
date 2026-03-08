"""
Banned Pharma RAG API — Main Application Entry Point.

FastAPI application with:
  • 4 API endpoints matching the existing frontend
  • CORS middleware
  • Structured logging
  • Global exception handlers
  • Health check endpoint
  • OpenAPI docs at /docs
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.models.schemas import HealthResponse

# ╔════════════════════════════════════════════════════════════════════╗
# ║  Logging Setup                                                     ║
# ╚════════════════════════════════════════════════════════════════════╝


def setup_logging():
    """Configure structured logging for the application."""
    settings = get_settings()

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
    )

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


# ╔════════════════════════════════════════════════════════════════════╗
# ║  Application Lifespan                                              ║
# ╚════════════════════════════════════════════════════════════════════╝


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger = setup_logging()
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("  Banned Pharma RAG API — Starting")
    logger.info("  Port: %s", settings.PORT)
    logger.info("  Region: %s", settings.AWS_REGION)
    logger.info("  KB ID: %s", settings.BEDROCK_KB_ID)
    logger.info("  Model: %s", settings.BEDROCK_MODEL_ID)
    logger.info("  CORS: %s", settings.CORS_ORIGINS)
    logger.info("=" * 60)

    yield  # Application is running

    logger.info("Banned Pharma RAG API — Shutting down")


# ╔════════════════════════════════════════════════════════════════════╗
# ║  FastAPI Application                                               ║
# ╚════════════════════════════════════════════════════════════════════╝

app = FastAPI(
    title="Banned Pharma RAG API",
    description=(
        "Indian pharmaceutical regulatory compliance API powered by "
        "AWS Bedrock Knowledge Base (Kendra GenAI Index). "
        "Provides RAG-based search of CDSCO banned drugs, gazette notifications, "
        "and regulatory documents."
    ),
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS Middleware ──────────────────────────────────────────────────

def _get_cors_origins():
    """Get CORS origins (called at import time)."""
    try:
        settings = get_settings()
        return settings.cors_origin_list
    except Exception:
        return ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Include API Routes ──────────────────────────────────────────────

app.include_router(api_router)


# ╔════════════════════════════════════════════════════════════════════╗
# ║  Health Check                                                      ║
# ╚════════════════════════════════════════════════════════════════════╝


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health_check():
    """Application health check endpoint."""
    try:
        settings = get_settings()
        kb_id = settings.BEDROCK_KB_ID
    except Exception:
        kb_id = None

    return HealthResponse(
        status="healthy",
        service="knowledge-base-aws",
        version="1.2.0",
        bedrock_kb_id=kb_id,
    )


# ╔════════════════════════════════════════════════════════════════════╗
# ║  Global Exception Handlers                                        ║
# ╚════════════════════════════════════════════════════════════════════╝


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with a clean JSON response."""
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error.get("loc", []))
        errors.append({
            "field": field,
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "unknown"),
        })

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception: %s", str(exc))

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ╔════════════════════════════════════════════════════════════════════╗
# ║  Entrypoint (python -m app.main)                                   ║
# ╚════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
