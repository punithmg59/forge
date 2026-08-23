from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

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
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

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
