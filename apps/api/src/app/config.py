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
