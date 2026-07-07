"""TOTP MFA service with backup codes (RFC 6238).

Security invariants:
- MFA secrets stored encrypted with Fernet symmetric encryption.
- Backup codes stored as bcrypt hashes (cost 12).
- Credentials (secrets, backup codes in plaintext) NEVER logged.
- TOTP codes are single-use: each timecode is tracked in Valkey (RFC 6238 §5.2).
"""

import logging
import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Protocol

import bcrypt
import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_mfa_encryption_key, get_valkey_url
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Backup code configuration
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8
BACKUP_CODE_ALPHABET = string.ascii_uppercase + string.digits

# bcrypt cost factor for backup codes
BCRYPT_COST_FACTOR = 12

# TOTP issuer name shown in authenticator apps
TOTP_ISSUER = "AI Finland"

# TOTP window tolerance (1 = accept 1 step before/after current)
TOTP_VALID_WINDOW = 1

# TOTP step duration in seconds (RFC 6238 default)
TOTP_STEP_SECONDS = 30

# TTL for used-TOTP cache entries: covers the full valid window (step * (2*window + 1))
# With window=1: 3 steps × 30s = 90s ensures every accepted timecode is tracked
# until it can no longer be accepted.
TOTP_REPLAY_TTL_SECONDS = TOTP_STEP_SECONDS * (2 * TOTP_VALID_WINDOW + 1)

# Roles that require MFA
MFA_REQUIRED_ROLES = {"admin", "super_admin"}


class ValkeyClient(Protocol):
    """Protocol for Valkey client operations used by MFAService."""

    def set(self, name: str, value: str, ex: int | None = None) -> Any: ...  # noqa: E704
    def get(self, name: str) -> Any: ...  # noqa: E704


class MFAError(Exception):
    """Base MFA error."""


class MFANotSetupError(MFAError):
    """Raised when MFA is not set up for a user."""


class MFAAlreadyEnabledError(MFAError):
    """Raised when MFA is already enabled."""


class InvalidMFACodeError(MFAError):
    """Raised when an MFA code is invalid."""


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key."""
    key = get_mfa_encryption_key()
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt_secret(secret: str) -> str:
    """Encrypt a TOTP secret with Fernet."""
    fernet = _get_fernet()
    return fernet.encrypt(secret.encode("utf-8")).decode("utf-8")


def _decrypt_secret(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted TOTP secret."""
    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise MFAError("Failed to decrypt MFA secret") from e


def _generate_backup_codes() -> list[str]:
    """Generate 10 cryptographically random 8-character alphanumeric backup codes."""
    return [
        "".join(secrets.choice(BACKUP_CODE_ALPHABET) for _ in range(BACKUP_CODE_LENGTH))
        for _ in range(BACKUP_CODE_COUNT)
    ]


def _hash_backup_code(code: str) -> str:
    """Hash a backup code with bcrypt cost 12."""
    salt = bcrypt.gensalt(rounds=BCRYPT_COST_FACTOR)
    return bcrypt.hashpw(code.encode("utf-8"), salt).decode("utf-8")


def _verify_backup_code(code: str, hashed: str) -> bool:
    """Verify a backup code against its bcrypt hash."""
    return bcrypt.checkpw(code.encode("utf-8"), hashed.encode("utf-8"))


class MFAService:
    """TOTP MFA service with single-use backup codes.

    Manages MFA setup, confirmation, and verification for users.
    Secrets are Fernet-encrypted at rest; backup codes are bcrypt-hashed.
    TOTP codes are single-use: each accepted timecode is recorded in Valkey
    with a TTL of TOTP_REPLAY_TTL_SECONDS to prevent replay attacks (RFC 6238 §5.2).
    """

    def __init__(
        self,
        user_repo: UserRepository,
        valkey_client: ValkeyClient | None = None,
    ) -> None:
        self._user_repo = user_repo
        if valkey_client is not None:
            self._valkey: ValkeyClient = valkey_client
        else:
            import valkey as valkey_lib

            url = get_valkey_url()
            self._valkey = valkey_lib.from_url(url)  # type: ignore[no-untyped-call]

    def _totp_used_key(self, user_id: str, timecode: int) -> str:
        """Build the Valkey key for a used TOTP timecode."""
        return f"totp_used:{user_id}:{timecode}"

    def _is_totp_replayed(self, user_id: str, timecode: int) -> bool:
        """Return True if this timecode has already been used (replay detected)."""
        key = self._totp_used_key(user_id, timecode)
        return self._valkey.get(key) is not None

    def _mark_totp_used(self, user_id: str, timecode: int) -> None:
        """Record a timecode as used in Valkey with TTL to prevent replay."""
        key = self._totp_used_key(user_id, timecode)
        self._valkey.set(key, "1", ex=TOTP_REPLAY_TTL_SECONDS)

    async def setup_mfa(self, user_id: str) -> dict[str, object]:
        """Begin MFA setup for a user.

        Generates a TOTP secret and 10 backup codes. Stores the encrypted
        secret and hashed backup codes on the user record. Does NOT enable
        MFA -- the user must confirm with a valid TOTP code first.

        Returns:
            Dict with 'secret', 'provisioning_uri', and 'backup_codes'
            (plaintext -- shown once, never stored in plaintext).

        Raises:
            MFAAlreadyEnabledError: If MFA is already enabled.
        """
        user = await self._user_repo.find_by_id(uuid.UUID(user_id))
        if user is None:
            raise MFAError(f"User not found: user_id={user_id}")

        if user.mfa_enabled:
            raise MFAAlreadyEnabledError("MFA is already enabled for this user")

        # Generate TOTP secret
        secret = pyotp.random_base32()

        # Generate provisioning URI for QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=TOTP_ISSUER,
        )

        # Generate backup codes (plaintext -- returned once, never logged)
        backup_codes = _generate_backup_codes()
        hashed_codes = [_hash_backup_code(code) for code in backup_codes]

        # Store encrypted secret and hashed backup codes (MFA not yet enabled)
        user.mfa_secret = _encrypt_secret(secret)
        user.mfa_backup_codes = hashed_codes  # type: ignore[assignment]
        user.mfa_enabled = False
        await self._user_repo.update(user)

        logger.info("MFA setup initiated: user_id=%s", user_id)

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "backup_codes": backup_codes,
        }

    async def confirm_mfa_setup(self, user_id: str, totp_code: str) -> bool:
        """Confirm MFA setup by verifying the first TOTP code.

        If the code is valid, sets mfa_enabled=True on the user record.

        Returns:
            True if setup was confirmed successfully.

        Raises:
            MFANotSetupError: If MFA has not been set up (no secret stored).
            InvalidMFACodeError: If the TOTP code is invalid.
        """
        user = await self._user_repo.find_by_id(uuid.UUID(user_id))
        if user is None:
            raise MFAError(f"User not found: user_id={user_id}")

        if not user.mfa_secret:
            raise MFANotSetupError("MFA setup has not been initiated for this user")

        secret = _decrypt_secret(user.mfa_secret)
        totp = pyotp.TOTP(secret)

        if not totp.verify(totp_code, valid_window=TOTP_VALID_WINDOW):
            logger.info("MFA confirmation failed (invalid code): user_id=%s", user_id)
            raise InvalidMFACodeError("Invalid TOTP code")

        user.mfa_enabled = True
        await self._user_repo.update(user)

        logger.info("MFA enabled: user_id=%s", user_id)
        return True

    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify an MFA code (TOTP or backup code).

        Checks the code as a TOTP first. If that fails, checks against the
        stored backup codes. A matching backup code is consumed (removed).

        TOTP codes are single-use per RFC 6238 §5.2: once a timecode is
        accepted it is recorded in Valkey with a TTL of TOTP_REPLAY_TTL_SECONDS.
        Any subsequent attempt with the same timecode is rejected as a replay.

        Returns:
            True if the code is valid, False otherwise.
        """
        user = await self._user_repo.find_by_id(uuid.UUID(user_id))
        if user is None:
            logger.warning("MFA verify: user not found: user_id=%s", user_id)
            return False

        if not user.mfa_secret:
            logger.warning("MFA verify: no secret stored: user_id=%s", user_id)
            return False

        secret = _decrypt_secret(user.mfa_secret)
        totp = pyotp.TOTP(secret)

        # Check TOTP code first
        if totp.verify(code, valid_window=TOTP_VALID_WINDOW):
            # Identify the single timecode that actually matched.
            # pyotp.verify() with valid_window=1 accepts offsets -1, 0, +1 from now.
            # We check each offset with valid_window=0 (exact match only) to find
            # the one step whose code equals the submitted value, then mark only
            # that timecode used.  This avoids blocking the *next* legitimate step
            # (T+1) when the user happened to submit a code from step T or T-1.
            now = datetime.now()
            current_timecode = totp.timecode(now)
            matched_timecode = current_timecode  # fallback: current step
            for offset in range(-TOTP_VALID_WINDOW, TOTP_VALID_WINDOW + 1):
                shifted = now + timedelta(seconds=offset * TOTP_STEP_SECONDS)
                if totp.verify(code, for_time=shifted, valid_window=0):
                    matched_timecode = current_timecode + offset
                    break

            # Reject if this specific timecode was already used (replay attack)
            if self._is_totp_replayed(user_id, matched_timecode):
                logger.warning(
                    "TOTP replay attack detected: user_id=%s", user_id
                )
                return False

            # Mark only the matched timecode as used to prevent replay
            self._mark_totp_used(user_id, matched_timecode)

            logger.info("MFA verified via TOTP: user_id=%s", user_id)
            return True

        # Fall back to backup codes
        backup_codes: list[str] = user.mfa_backup_codes or []  # type: ignore[assignment]
        for i, hashed in enumerate(backup_codes):
            if _verify_backup_code(code, hashed):
                # Consume the backup code (remove from list)
                remaining = backup_codes[:i] + backup_codes[i + 1 :]
                user.mfa_backup_codes = remaining  # type: ignore[assignment]
                await self._user_repo.update(user)
                logger.info(
                    "MFA verified via backup code: user_id=%s, remaining=%d",
                    user_id,
                    len(remaining),
                )
                return True

        logger.info("MFA verification failed: user_id=%s", user_id)
        return False

    def is_mfa_required(self, roles: list[str]) -> bool:
        """Return True if any of the given roles require MFA.

        MFA is mandatory for 'admin' and 'super_admin' roles.
        """
        return bool(MFA_REQUIRED_ROLES.intersection(roles))

    def is_mfa_setup_complete(self, user: User) -> bool:
        """Return True if MFA has been fully set up and enabled for the user."""
        return user.mfa_enabled is True
