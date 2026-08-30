import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Forge API",
    description="The backend service for Forge — The Operating System for Ambitious Solo Founders.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred."},
    )


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

HEALTH_RESPONSE = {"status": "ok", "service": "forge-api"}


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Root health check — used by the frontend status indicator."""
    return HEALTH_RESPONSE


@app.get("/api/v1/health", tags=["health"])
async def health_v1() -> dict:
    """Versioned health check endpoint."""
    return HEALTH_RESPONSE
