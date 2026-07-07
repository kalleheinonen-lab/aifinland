"""CORS middleware configuration.

Reads CORS_ALLOWED_ORIGINS from environment. Raises on startup if unset.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins from environment.

    Raises:
        RuntimeError: If CORS_ALLOWED_ORIGINS is not set.
    """
    origins = os.environ.get("CORS_ALLOWED_ORIGINS")
    if not origins:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS environment variable is required but not set."
        )
    return [o.strip() for o in origins.split(",") if o.strip()]


def add_cors_middleware(app: FastAPI) -> None:
    """Add CORS middleware to the FastAPI app."""
    origins = get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
