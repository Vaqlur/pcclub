"""Tokens, password/OTP hashing and IIN protection.

The IIN is personal data: it is stored encrypted (Fernet) plus an HMAC for uniqueness
lookups, returned only masked, and must never be logged.
"""

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.fernet import Fernet

from app.core.config import Settings

SubjectType = Literal["customer", "staff"]
_JWT_ALG = "HS256"
_password_hasher = PasswordHasher()


# --- access tokens ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenClaims:
    subject_id: uuid.UUID
    subject_type: SubjectType


class InvalidToken(Exception):
    pass


def create_access_token(
    settings: Settings, *, subject_id: uuid.UUID, subject_type: SubjectType, now: datetime
) -> str:
    payload = {
        "sub": str(subject_id),
        "typ": subject_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALG)


def decode_access_token(settings: Settings, token: str, *, now: datetime) -> TokenClaims:
    """Verify signature and expiry. Expiry is checked against the injected clock."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_JWT_ALG],
            options={"verify_exp": False, "verify_iat": False, "require": ["sub", "typ", "exp"]},
        )
        if int(payload["exp"]) <= int(now.timestamp()):
            raise InvalidToken("expired")
        if payload["typ"] not in ("customer", "staff"):
            raise InvalidToken("unknown subject type")
        return TokenClaims(subject_id=uuid.UUID(payload["sub"]), subject_type=payload["typ"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        raise InvalidToken(str(exc)) from exc


# --- refresh tokens / OTP --------------------------------------------------------------------


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Refresh tokens are high-entropy, so a plain SHA-256 is sufficient."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(settings: Settings, phone: str, code: str) -> str:
    return hmac.new(
        settings.jwt_secret.encode(), f"otp:{phone}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# --- staff passwords -------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerificationError, ValueError:
        return False


# --- IIN -------------------------------------------------------------------------------------


def _fernet(settings: Settings) -> Fernet:
    if settings.iin_encryption_key:
        return Fernet(settings.iin_encryption_key.encode())
    # Dev/test only: Settings refuses to start in prod without a real key.
    derived = base64.urlsafe_b64encode(hashlib.sha256(b"pcclub-dev-iin-key").digest())
    return Fernet(derived)


def encrypt_iin(settings: Settings, iin: str) -> str:
    return _fernet(settings).encrypt(iin.encode()).decode()


def decrypt_iin(settings: Settings, token: str) -> str:
    return _fernet(settings).decrypt(token.encode()).decode()


def hash_iin(settings: Settings, iin: str) -> str:
    return hmac.new(settings.iin_hash_pepper.encode(), iin.encode(), hashlib.sha256).hexdigest()


def mask_iin(iin: str) -> str:
    return "*" * (len(iin) - 4) + iin[-4:]
