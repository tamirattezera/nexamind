from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True, slots=True)
class GenerationRateLimitConfig:
    limit: int
    window_seconds: int


def get_generation_rate_limit_config() -> GenerationRateLimitConfig:
    limit = settings.CHAT_GENERATION_RATE_LIMIT
    window_seconds = settings.CHAT_GENERATION_RATE_WINDOW_SECONDS

    if type(limit) is not int:
        raise ImproperlyConfigured(
            "CHAT_GENERATION_RATE_LIMIT must be an integer."
        )

    if limit <= 0:
        raise ImproperlyConfigured(
            "CHAT_GENERATION_RATE_LIMIT must be greater than zero."
        )

    if type(window_seconds) is not int:
        raise ImproperlyConfigured(
            "CHAT_GENERATION_RATE_WINDOW_SECONDS must be an integer."
        )

    if window_seconds <= 0:
        raise ImproperlyConfigured(
            "CHAT_GENERATION_RATE_WINDOW_SECONDS must be greater than zero."
        )

    return GenerationRateLimitConfig(
        limit=limit,
        window_seconds=window_seconds,
    )
