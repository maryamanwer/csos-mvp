"""Credential protection primitives for CSOS data-source integrations."""
from __future__ import annotations

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_ENVELOPE = "enc:v1:"
_MASK = "••••••••"


class SecretDecryptionError(ValueError):
    pass


def _cipher_ring() -> list[Fernet]:
    ring: list[Fernet] = []
    for secret in settings.connector_encryption_keys:
        material = hashlib.sha256(secret.encode("utf-8")).digest()
        ring.append(Fernet(base64.urlsafe_b64encode(material)))
    if not ring:
        raise RuntimeError("At least one connector encryption key is required")
    return ring


def encrypt_secret(value: str | None) -> str | None:
    if value in (None, "") or str(value).startswith(_ENVELOPE):
        return value
    ciphertext = _cipher_ring()[0].encrypt(str(value).encode()).decode()
    return _ENVELOPE + ciphertext


def decrypt_secret(value: str | None) -> str | None:
    if value in (None, ""):
        return value
    encoded = str(value)
    if not encoded.startswith(_ENVELOPE):
        raise SecretDecryptionError("Connector credential is not encrypted")
    payload = encoded.removeprefix(_ENVELOPE).encode()
    for cipher in _cipher_ring():
        try:
            return cipher.decrypt(payload).decode()
        except InvalidToken:
            pass
    raise SecretDecryptionError("Connector credential cannot be opened with the active key ring")


def _transform(config: dict, secret_fields: set[str], operation) -> dict:
    return {
        key: operation(value) if key in secret_fields else value
        for key, value in dict(config or {}).items()
    }


def encrypt_config(config: dict, secret_fields: set[str]) -> dict:
    return _transform(config, secret_fields, encrypt_secret)


def decrypt_config(config: dict, secret_fields: set[str]) -> dict:
    return _transform(config, secret_fields, decrypt_secret)


def redact_config(config: dict, secret_fields: set[str]) -> dict:
    return _transform(config, secret_fields, lambda value: _MASK if value else value)


def generate_api_key() -> str:
    return f"csos_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()
