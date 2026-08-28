"""Symmetric encryption for stored connector credentials.

Connector configurations hold device passwords, SNMP community strings and
SNMPv3 keys. Those must never sit in the database as plaintext, and they must
never leave the API in a response body.

Connector encryption is deliberately independent from JWT signing. A
comma-separated key ring supports safe rotation: the first key encrypts new
values and every retained key may decrypt existing records.
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

PREFIX = "enc:v1:"


class SecretDecryptionError(ValueError):
    """Stored connector credentials cannot be decrypted with the active key ring."""


def _fernets() -> tuple[Fernet, ...]:
    keys = settings.connector_encryption_keys
    if not keys:
        raise RuntimeError("CONNECTOR_ENCRYPTION_KEYS must contain at least one key")
    return tuple(
        Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest()))
        for key in keys
    )


def encrypt_secret(value: str | None) -> str | None:
    if value in (None, ""):
        return value
    if isinstance(value, str) and value.startswith(PREFIX):
        return value  # already encrypted; re-encrypting would double-wrap
    token = _fernets()[0].encrypt(str(value).encode("utf-8")).decode("utf-8")
    return f"{PREFIX}{token}"


def decrypt_secret(value: str | None) -> str | None:
    if value in (None, ""):
        return value
    if not str(value).startswith(PREFIX):
        raise SecretDecryptionError("Stored connector credential is not encrypted")
    token = str(value)[len(PREFIX) :]
    for fernet in _fernets():
        try:
            return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            continue
    logger.warning("Unable to decrypt a connector credential with the configured key ring")
    raise SecretDecryptionError(
        "Connector credential cannot be decrypted; retain the prior rotation key or re-enter it"
    )


def encrypt_config(config: dict, secret_fields: set[str]) -> dict:
    """Return a copy of ``config`` with the named fields encrypted."""
    return {
        key: (encrypt_secret(value) if key in secret_fields else value)
        for key, value in (config or {}).items()
    }


def decrypt_config(config: dict, secret_fields: set[str]) -> dict:
    """Return a copy of ``config`` with the named fields decrypted."""
    return {
        key: (decrypt_secret(value) if key in secret_fields else value)
        for key, value in (config or {}).items()
    }


def redact_config(config: dict, secret_fields: set[str]) -> dict:
    """Return a copy safe to send to a client — secrets replaced by a marker."""
    return {
        key: ("••••••••" if key in secret_fields and value else value)
        for key, value in (config or {}).items()
    }


def generate_api_key() -> str:
    """Create an agent enrolment key."""
    import secrets

    return "csos_" + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Store only the hash, so a database leak does not yield usable keys."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
