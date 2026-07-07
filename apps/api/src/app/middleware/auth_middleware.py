"""JWT authentication middleware.

Extracts Bearer token from Authorization header, verifies via TokenService,
and returns user payload. Enforces MFA setup requirement for admin roles.
"""

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.token_service import TokenService, TokenVerificationError

logger = logging.getLogger(__name__)

# Roles that require MFA to be enabled
MFA_REQUIRED_ROLES = {"admin", "super_admin"}

# Endpoints exempt from MFA setup requirement
MFA_SETUP_EXEMPT_PATHS = {"/v1/auth/mfa/setup", "/v1/auth/mfa/setup/confirm"}

security = HTTPBearer(auto_error=False)


def _get_token_service() -> TokenService:
    """Get a TokenService instance."""
    return TokenService()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token_service: TokenService = Depends(_get_token_service),
) -> dict[str, Any]:
    """Validate JWT and return user payload.

    Returns:
        Dict with sub, org, roles from the JWT payload.

    Raises:
        HTTPException 401: If token is missing or invalid.
        HTTPException 403: If admin/super_admin without MFA enabled
                          (except on MFA setup endpoints).
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Missing authentication token"},
        )

    try:
        payload = token_service.verify_access_token(credentials.credentials)
    except TokenVerificationError:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"},
        )

    user_roles: list[str] = payload.get("roles", [])
    mfa_enabled = payload.get("mfa_enabled", False)

    # Check MFA requirement for admin roles (except on MFA setup endpoints)
    if (
        MFA_REQUIRED_ROLES.intersection(user_roles)
        and not mfa_enabled
        and request.url.path not in MFA_SETUP_EXEMPT_PATHS
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "MFA_SETUP_REQUIRED",
                "message": "MFA setup is required for admin users",
            },
        )

    return {
        "sub": payload.get("sub"),
        "org": payload.get("org"),
        "roles": user_roles,
    }
