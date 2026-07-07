"""Application configuration from environment variables."""

import os


class ConfigError(Exception):
    """Raised when a required configuration value is missing."""


def get_jwt_private_key() -> str:
    """Get RSA private key for JWT signing from environment."""
    key = os.environ.get("JWT_PRIVATE_KEY")
    if not key:
        raise ConfigError(
            "JWT_PRIVATE_KEY environment variable is required but not set."
        )
    return key


def get_jwt_public_key() -> str:
    """Get RSA public key for JWT verification from environment."""
    key = os.environ.get("JWT_PUBLIC_KEY")
    if not key:
        raise ConfigError(
            "JWT_PUBLIC_KEY environment variable is required but not set."
        )
    return key


def get_valkey_url() -> str:
    """Get Valkey connection URL from environment."""
    url = os.environ.get("VALKEY_URL")
    if not url:
        raise ConfigError("VALKEY_URL environment variable is required but not set.")
    return url


def get_mfa_encryption_key() -> str:
    """Get Fernet encryption key for MFA secrets from environment.

    The key must be a URL-safe base64-encoded 32-byte value, as produced
    by Fernet.generate_key().
    """
    key = os.environ.get("MFA_ENCRYPTION_KEY")
    if not key:
        raise ConfigError(
            "MFA_ENCRYPTION_KEY environment variable is required but not set."
        )
    return key
