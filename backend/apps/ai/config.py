from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ALLOWED_THINKING_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    api_key: str
    model: str
    thinking_level: str
    max_output_tokens: int
    timeout_ms: int


def get_gemini_config() -> GeminiConfig:
    api_key = settings.GEMINI_API_KEY.strip()
    model = settings.GEMINI_MODEL.strip()
    thinking_level = settings.GEMINI_THINKING_LEVEL

    if not api_key:
        raise ImproperlyConfigured("GEMINI_API_KEY must be configured.")

    if not model:
        raise ImproperlyConfigured("GEMINI_MODEL must not be empty.")

    if thinking_level not in ALLOWED_THINKING_LEVELS:
        raise ImproperlyConfigured(
            "GEMINI_THINKING_LEVEL must be LOW, MEDIUM, or HIGH."
        )

    if settings.GEMINI_MAX_OUTPUT_TOKENS <= 0:
        raise ImproperlyConfigured(
            "GEMINI_MAX_OUTPUT_TOKENS must be greater than zero."
        )

    if settings.GEMINI_TIMEOUT_MS <= 0:
        raise ImproperlyConfigured("GEMINI_TIMEOUT_MS must be greater than zero.")

    return GeminiConfig(
        api_key=api_key,
        model=model,
        thinking_level=thinking_level,
        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        timeout_ms=settings.GEMINI_TIMEOUT_MS,
    )
