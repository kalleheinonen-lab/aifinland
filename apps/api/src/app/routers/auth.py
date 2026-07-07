"""Authentication router with all auth endpoints.

Prefix: /v1/auth
All responses follow the standard envelope: {data, meta, error}.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.middleware.auth_middleware import get_current_user
from app.schemas.auth import (
    AuthTokensResponse,
    ErrorDetail,
    LoginRequest,
    MetaResponse,
    MFARequiredResponse,
    MFASetupConfirmRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequestModel,
    RefreshTokenRequest,
    RegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _build_meta(request: Request) -> MetaResponse:
    """Build response metadata with request ID and timestamp."""
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    return MetaResponse(
        requestId=request_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


def _success_response(
    data: Any, request: Request, status_code: int = 200,
) -> dict[str, Any]:
    """Build a success response envelope."""
    return {
        "data": data,
        "meta": _build_meta(request).model_dump(by_alias=True),
        "error": None,
    }


def _error_response(
    code: str, message: str, request: Request, details: list[str] | None = None
) -> dict[str, Any]:
    """Build an error response envelope."""
    return {
        "data": None,
        "meta": _build_meta(request).model_dump(by_alias=True),
        "error": ErrorDetail(
            code=code, message=message, details=details or []
        ).model_dump(),
    }


# --- Dependency injection helpers ---
# These are overridden in tests to inject mocks.


async def _get_db_session():  # type: ignore[no-untyped-def]  # noqa: ANN204
    """Yield an async database session for the request lifetime."""
    from app.db import create_engine, create_session_factory

    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        async with session.begin():
            yield session


async def _get_auth_service(session: Any = Depends(_get_db_session)) -> Any:
    """Get AuthService instance wired with real DB and Valkey connections."""
    from app.repositories.user_repository import UserRepository
    from app.services.auth_service import AuthService
    from app.services.rate_limit_service import RateLimitService
    from app.services.session_service import SessionService
    from app.services.token_service import TokenService

    user_repo = UserRepository(session)
    token_service = TokenService()
    session_service = SessionService()
    rate_limit_service = RateLimitService()
    return AuthService(
        user_repo=user_repo,
        token_service=token_service,
        session_service=session_service,
        rate_limit_service=rate_limit_service,
    )


async def _get_mfa_service(session: Any = Depends(_get_db_session)) -> Any:
    """Get MFAService instance wired with real DB connection."""
    from app.repositories.user_repository import UserRepository
    from app.services.mfa_service import MFAService

    user_repo = UserRepository(session)
    return MFAService(user_repo=user_repo)


def _get_token_service() -> Any:
    """Get TokenService instance. Overridden in tests."""
    from app.services.token_service import TokenService

    return TokenService()


# --- Endpoints ---


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
) -> dict[str, Any]:
    """Register a new user.

    Returns 201 with tokens and user info on success.
    Returns 409 on duplicate email.
    """
    from app.services.auth_service import EmailAlreadyExistsError

    try:
        result = await auth_service.register(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error_response(
                code="EMAIL_EXISTS",
                message="An account with this email already exists",
                request=request,
            ),
        )

    user_data = UserResponse(
        id=result["user_id"],
        email=result["email"],
        display_name=body.display_name,
        email_verified=False,
        mfa_enabled=False,
    )
    data = AuthTokensResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user=user_data,
    )
    return _success_response(data.model_dump(), request)


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
) -> dict[str, Any]:
    """Verify email with token.

    Returns 200 on success, 400 on invalid/expired token.
    """
    from app.services.auth_service import InvalidTokenError

    try:
        await auth_service.verify_email(body.token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_response(
                code="INVALID_TOKEN",
                message="Invalid or expired verification token",
                request=request,
            ),
        )

    return _success_response({"verified": True}, request)


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
    token_service: Any = Depends(_get_token_service),
) -> dict[str, Any]:
    """Login with email and password.

    Returns tokens on success without MFA.
    Returns mfa_required response if MFA is enabled.
    Returns 401 on invalid credentials or locked account.
    """
    from app.services.auth_service import (
        AccountLockedError,
        InvalidCredentialsError,
        MfaChallengeRequiredError,
    )

    try:
        result = await auth_service.login(
            email=body.email,
            password=body.password,
        )
    except (InvalidCredentialsError, AccountLockedError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="INVALID_CREDENTIALS",
                message="Invalid credentials",
                request=request,
            ),
        )
    except MfaChallengeRequiredError as e:
        # Issue a short-lived MFA challenge token
        mfa_token = token_service.create_access_token(
            user_id=e.user_id,
            org_id=None,
            roles=["mfa_challenge"],
        )
        data = MFARequiredResponse(mfa_required=True, mfa_token=mfa_token)
        return _success_response(data.model_dump(), request)

    user_data = UserResponse(
        id=result["user_id"],
        email=result["email"],
    )
    tokens_data = AuthTokensResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user=user_data,
    )
    return _success_response(tokens_data.model_dump(), request)


@router.post("/mfa/verify")
async def mfa_verify(
    body: MFAVerifyRequest,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
    mfa_service: Any = Depends(_get_mfa_service),
    token_service: Any = Depends(_get_token_service),
) -> dict[str, Any]:
    """Verify MFA code after login.

    Returns full tokens on success, 401 on failure.
    """
    from app.services.token_service import TokenVerificationError

    # Verify the MFA challenge token
    try:
        payload = token_service.verify_access_token(body.mfa_token)
    except TokenVerificationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="INVALID_MFA_TOKEN",
                message="Invalid or expired MFA token",
                request=request,
            ),
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="INVALID_MFA_TOKEN",
                message="Invalid MFA token",
                request=request,
            ),
        )

    # Verify the TOTP/backup code
    is_valid = await mfa_service.verify_mfa(user_id, body.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="INVALID_MFA_CODE",
                message="Invalid MFA code",
                request=request,
            ),
        )

    # Issue full tokens via auth_service
    # The auth_service._issue_tokens needs a user object, so we use a
    # dedicated method that issues tokens given a user_id after MFA success.
    try:
        result = await auth_service.issue_tokens_for_user(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="AUTH_ERROR",
                message="Authentication failed",
                request=request,
            ),
        )

    user_data = UserResponse(
        id=result["user_id"],
        email=result["email"],
    )
    data = AuthTokensResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user=user_data,
    )
    return _success_response(data.model_dump(), request)


@router.post("/mfa/setup")
async def mfa_setup(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    mfa_service: Any = Depends(_get_mfa_service),
) -> dict[str, Any]:
    """Set up MFA for the authenticated user.

    Returns secret, provisioning URI, and backup codes.
    """
    from app.services.mfa_service import MFAAlreadyEnabledError

    user_id = current_user["sub"]

    try:
        result = await mfa_service.setup_mfa(user_id)
    except MFAAlreadyEnabledError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error_response(
                code="MFA_ALREADY_ENABLED",
                message="MFA is already enabled for this account",
                request=request,
            ),
        )

    data = MFASetupResponse(
        secret=result["secret"],
        provisioning_uri=result["provisioning_uri"],
        backup_codes=result["backup_codes"],
    )
    return _success_response(data.model_dump(), request)


@router.post("/mfa/setup/confirm")
async def mfa_setup_confirm(
    body: MFASetupConfirmRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    mfa_service: Any = Depends(_get_mfa_service),
) -> dict[str, Any]:
    """Confirm MFA setup with a TOTP code.

    Returns 200 on success, 400 on invalid code.
    """
    from app.services.mfa_service import InvalidMFACodeError, MFANotSetupError

    user_id = current_user["sub"]

    try:
        await mfa_service.confirm_mfa_setup(user_id, body.code)
    except (InvalidMFACodeError, MFANotSetupError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_response(
                code="INVALID_MFA_CODE",
                message="Invalid MFA code or MFA not set up",
                request=request,
            ),
        )

    return _success_response({"mfa_enabled": True}, request)


@router.post("/refresh")
async def refresh(
    body: RefreshTokenRequest,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
    token_service: Any = Depends(_get_token_service),
) -> dict[str, Any]:
    """Refresh access token using refresh token.

    Returns new token pair on success, 401 on invalid token.
    """
    from app.services.auth_service import InvalidTokenError

    # We need to know the user_id to validate the refresh token.
    # Extract from the Authorization header if present, or from the
    # refresh token's associated session.
    # For this implementation, we require the access token in the header
    # to identify the user (even if expired, we can decode without verification).
    auth_header = request.headers.get("Authorization", "")
    user_id: str | None = None

    if auth_header.startswith("Bearer "):
        try:
            import jwt as pyjwt

            # Decode without verification to get user_id (token may be expired)
            payload = pyjwt.decode(
                auth_header[7:],
                options={"verify_signature": False, "verify_exp": False},
            )
            user_id = payload.get("sub")
        except Exception:
            pass

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="INVALID_TOKEN",
                message="Unable to identify user for token refresh",
                request=request,
            ),
        )

    try:
        result = await auth_service.refresh_token(body.refresh_token, user_id)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_response(
                code="INVALID_TOKEN",
                message="Invalid refresh token",
                request=request,
            ),
        )

    return _success_response(
        {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
        },
        request,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    auth_service: Any = Depends(_get_auth_service),
) -> None:
    """Logout and invalidate the refresh token.

    Returns 204 on success.
    """
    # Get refresh token from request body
    try:
        body_bytes = await request.body()
        if body_bytes:
            import json

            body = json.loads(body_bytes)
            refresh_token = body.get("refresh_token", "")
        else:
            refresh_token = ""
    except Exception:
        refresh_token = ""

    user_id = current_user["sub"]
    if refresh_token:
        await auth_service.logout(user_id, refresh_token)


@router.post("/password-reset/request")
async def password_reset_request(
    body: PasswordResetRequestModel,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
) -> dict[str, Any]:
    """Request a password reset.

    Always returns 200 (silent success to prevent email enumeration).
    """
    await auth_service.request_password_reset(body.email)
    msg = "If the email exists, a reset link was sent"
    return _success_response({"message": msg}, request)


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    body: PasswordResetConfirmRequest,
    request: Request,
    auth_service: Any = Depends(_get_auth_service),
) -> dict[str, Any]:
    """Confirm password reset with token and new password.

    Returns 200 on success, 400 on invalid/expired token.
    """
    from app.services.auth_service import InvalidTokenError

    try:
        await auth_service.confirm_password_reset(body.token, body.new_password)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_response(
                code="INVALID_TOKEN",
                message="Invalid or expired reset token",
                request=request,
            ),
        )

    return _success_response({"message": "Password has been reset"}, request)
