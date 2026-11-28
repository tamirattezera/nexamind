import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.checks import Error, Tags, register


REDIS_BACKEND = "django.core.cache.backends.redis.RedisCache"


@register(Tags.caches)
def check_production_cache(app_configs, **kwargs):
    """
    Verify that production uses a reachable Redis cache.

    Development and test configurations are intentionally exempt.
    """
    if not settings.IS_PRODUCTION:
        return []

    backend = settings.CACHES.get("default", {}).get("BACKEND")

    if backend != REDIS_BACKEND:
        return [
            Error(
                "Production must use the Redis cache backend.",
                hint="Configure CACHES['default'] with RedisCache.",
                id="accounts.E001",
            )
        ]

    key = f"nexamind:system-check:{secrets.token_hex(16)}"
    value = secrets.token_urlsafe(24)

    try:
        cache.set(key, value, timeout=10)

        if cache.get(key) != value:
            return [
                Error(
                    "The production Redis cache failed its write/read check.",
                    hint="Verify Redis connectivity and cache permissions.",
                    id="accounts.E002",
                )
            ]

    except Exception:
        return [
            Error(
                "The production Redis cache is unavailable.",
                hint="Verify REDIS_URL, Redis connectivity, and credentials.",
                id="accounts.E003",
            )
        ]

    finally:
        try:
            cache.delete(key)
        except Exception:
            pass

    return []
