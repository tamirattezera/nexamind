"""Utilities for idempotent message-generation requests."""

import hashlib
import uuid


def parse_idempotency_key(value: str) -> uuid.UUID:
    """Parse a UUID v4 idempotency key."""
    if not isinstance(value, str):
        raise ValueError("Idempotency key must be a UUID v4 string.")

    try:
        key = uuid.UUID(value)
    except ValueError:
        raise ValueError("Idempotency key must be a valid UUID v4.") from None

    if key.version != 4 or str(key) != value.lower():
        raise ValueError("Idempotency key must be a canonical UUID v4.")

    return key


def hash_message_content(content: str) -> str:
    """Return the SHA-256 hex digest of normalized message content."""
    if not isinstance(content, str):
        raise TypeError("Message content must be a string.")

    return hashlib.sha256(content.encode("utf-8")).hexdigest()
