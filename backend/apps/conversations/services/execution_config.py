from apps.ai.config import ALLOWED_THINKING_LEVELS, GeminiConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.conversations.models import ChatTurn


_REQUIRED_METADATA_KEYS = {
    "schema_version",
    "provider",
    "requested_model",
    "thinking_level",
}


def reconstruct_generation_config(chat_turn: ChatTurn) -> GeminiConfig:
    """
    Reconstruct the accepted generation configuration for a ChatTurn.

    Generation choices come from the persisted snapshot. Credentials and
    operational timeout come from current server settings.
    """
    metadata = chat_turn.generation_metadata

    if not isinstance(metadata, dict) or set(metadata) != _REQUIRED_METADATA_KEYS:
        raise ImproperlyConfigured(
            "ChatTurn generation metadata has an invalid structure."
        )

    schema_version = metadata["schema_version"]
    if type(schema_version) is not int or schema_version != 1:
        raise ImproperlyConfigured(
            "ChatTurn generation metadata has an unsupported schema version."
        )

    if metadata["provider"] != "gemini":
        raise ImproperlyConfigured(
            "ChatTurn generation metadata specifies an unsupported provider."
        )

    model = metadata["requested_model"]
    if (
        not isinstance(model, str)
        or not model
        or model != model.strip()
    ):
        raise ImproperlyConfigured(
            "ChatTurn requested model is missing or invalid."
        )

    thinking_level = metadata["thinking_level"]
    if (
        not isinstance(thinking_level, str)
        or thinking_level not in ALLOWED_THINKING_LEVELS
    ):
        raise ImproperlyConfigured(
            "ChatTurn thinking level is missing or invalid."
        )

    max_output_tokens = chat_turn.max_output_tokens
    if type(max_output_tokens) is not int or max_output_tokens <= 0:
        raise ImproperlyConfigured(
            "ChatTurn max_output_tokens must be a positive integer."
        )

    api_key = settings.GEMINI_API_KEY
    if not isinstance(api_key, str) or not api_key.strip():
        raise ImproperlyConfigured("GEMINI_API_KEY must be configured.")

    timeout_ms = settings.GEMINI_TIMEOUT_MS
    if type(timeout_ms) is not int or timeout_ms <= 0:
        raise ImproperlyConfigured(
            "GEMINI_TIMEOUT_MS must be a positive integer."
        )

    return GeminiConfig(
        api_key=api_key.strip(),
        model=model,
        thinking_level=thinking_level,
        max_output_tokens=max_output_tokens,
        timeout_ms=timeout_ms,
    )
