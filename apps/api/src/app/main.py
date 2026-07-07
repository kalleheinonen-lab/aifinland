"""AI Finland Matchmaking Platform API."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.middleware.cors import add_cors_middleware
from app.routers.auth import router as auth_router

REQUIRED_ENV_VARS: list[str] = ["CORS_ALLOWED_ORIGINS"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Validate required environment variables on startup."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    yield


app = FastAPI(title="AI Finland API", lifespan=lifespan)

# Add CORS middleware (reads CORS_ALLOWED_ORIGINS from env)
if os.environ.get("CORS_ALLOWED_ORIGINS"):
    add_cors_middleware(app)

# Register routers
app.include_router(auth_router)

# Conditionally register test-only helpers (NEVER in production)
if os.environ.get("APP_ENV") == "test":
    from app.routers.test_helpers import router as test_helpers_router

    app.include_router(test_helpers_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
