"""TEST ONLY - never register in production. Guarded by APP_ENV=test check in main.py.

This router provides test-only endpoints for the e2e test suite.
It is conditionally registered ONLY when APP_ENV=test.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth/_test", tags=["test-helpers"])


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Yield an async database session for the request lifetime."""
    from app.db import create_engine, create_session_factory

    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session


@router.get("/verification-token")
async def get_verification_token(
    email: str = Query(..., description="Email address to look up"),
    session: Any = Depends(_get_db_session),
) -> dict[str, str]:
    """Return the email verification token for a given email.

    TEST ONLY endpoint. Queries the database directly for the token stored
    during registration. Returns 404 if no token found for the email.
    """
    from sqlalchemy import select

    from app.models.user import User

    stmt = select(User.email_verification_token).where(
        User.email == email,
        User.deleted_at.is_(None),
        User.email_verification_token.is_not(None),
    )
    result = await session.execute(stmt)
    token = result.scalar_one_or_none()

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "No verification token found for this email",
                }
            },
        )
    return {"token": token}
