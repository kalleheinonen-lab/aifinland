"""Pydantic v2 request/response models for authentication endpoints."""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Password policy: min 12 chars, upper + lower + digit + symbol
PASSWORD_MIN_LENGTH = 12
PASSWORD_PATTERN_UPPER = re.compile(r"[A-Z]")
PASSWORD_PATTERN_LOWER = re.compile(r"[a-z]")
PASSWORD_PATTERN_DIGIT = re.compile(r"[0-9]")
PASSWORD_PATTERN_SYMBOL = re.compile(r"[^A-Za-z0-9]")


def validate_password_policy(password: str) -> str:
    """Validate password meets policy requirements."""
    errors: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if not PASSWORD_PATTERN_UPPER.search(password):
        errors.append("Password must contain at least one uppercase letter")
    if not PASSWORD_PATTERN_LOWER.search(password):
        errors.append("Password must contain at least one lowercase letter")
    if not PASSWORD_PATTERN_DIGIT.search(password):
        errors.append("Password must contain at least one digit")
    if not PASSWORD_PATTERN_SYMBOL.search(password):
        errors.append("Password must contain at least one symbol")
    if errors:
        raise ValueError("; ".join(errors))
    return password


# --- Request Models ---


class RegisterRequest(BaseModel):
    """Registration request."""

    model_config = ConfigDict(strict=True)

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return validate_password_policy(v)


class LoginRequest(BaseModel):
    """Login request."""

    model_config = ConfigDict(strict=True)

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str = Field(min_length=1, max_length=255)


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""

    mfa_token: str = Field(min_length=1, max_length=2048)
    code: str = Field(min_length=1, max_length=20)


class MFASetupConfirmRequest(BaseModel):
    """MFA setup confirmation request."""

    code: str = Field(min_length=1, max_length=20)


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(min_length=1, max_length=255)


class PasswordResetRequestModel(BaseModel):
    """Password reset request."""

    email: str = Field(min_length=1, max_length=320)


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation request."""

    token: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return validate_password_policy(v)


class ResendVerificationEmailRequest(BaseModel):
    """Resend verification email request."""

    email: str = Field(min_length=1, max_length=320)


# --- Response Models ---


class MetaResponse(BaseModel):
    """Response metadata."""

    request_id: str = Field(alias="requestId")
    timestamp: str

    model_config = ConfigDict(populate_by_name=True)


class ErrorDetail(BaseModel):
    """Error detail."""

    code: str
    message: str
    details: list[str] = Field(default_factory=list)


class APIResponse(BaseModel):
    """Standard API response envelope."""

    data: Any = None
    meta: MetaResponse
    error: ErrorDetail | None = None


class UserResponse(BaseModel):
    """User data in response."""

    id: str
    email: str
    display_name: str | None = None
    email_verified: bool = False
    mfa_enabled: bool = False
    created_at: datetime | None = None


class AuthTokensResponse(BaseModel):
    """Authentication tokens response data."""

    access_token: str
    refresh_token: str
    user: UserResponse


class MFARequiredResponse(BaseModel):
    """MFA challenge required response data."""

    mfa_required: bool = True
    mfa_token: str


class MFASetupResponse(BaseModel):
    """MFA setup response data."""

    secret: str
    provisioning_uri: str
    backup_codes: list[str]
