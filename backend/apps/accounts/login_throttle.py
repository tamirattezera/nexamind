import hashlib
import hmac
import math
import time

from django.conf import settings
from django.core.cache import cache


LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW_SECONDS = 900
LOGIN_COOLDOWN_SECONDS = 900


class LoginProtectionUnavailable(Exception):
    """Raised when login protection cannot access its cache backend."""


def _cache_keys(email, ip_address):
    normalized_email = (email or "").strip().lower()
    normalized_ip = (ip_address or "unknown").strip()

    identity = f"{normalized_email}\0{normalized_ip}".encode("utf-8")
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        identity,
        hashlib.sha256,
    ).hexdigest()

    prefix = f"accounts:login-protection:v1:{digest}"

    return f"{prefix}:failures", f"{prefix}:cooldown"


def _cache_operation(operation):
    try:
        return operation()
    except Exception as error:
        raise LoginProtectionUnavailable(
            "Login protection cache is unavailable."
        ) from error


def get_login_cooldown(email, ip_address):
    _, cooldown_key = _cache_keys(email, ip_address)

    cooldown_until = _cache_operation(
        lambda: cache.get(cooldown_key)
    )

    if cooldown_until is None:
        return 0

    try:
        remaining = math.ceil(float(cooldown_until) - time.time())
    except (TypeError, ValueError, OverflowError) as error:
        raise LoginProtectionUnavailable(
            "Login protection cache contains invalid cooldown data."
        ) from error

    if remaining <= 0:
        _cache_operation(lambda: cache.delete(cooldown_key))
        return 0

    return remaining


def record_failed_login(email, ip_address):
    failure_key, cooldown_key = _cache_keys(email, ip_address)

    def increment_counter():
        if cache.add(
            failure_key,
            1,
            timeout=LOGIN_FAILURE_WINDOW_SECONDS,
        ):
            return 1

        try:
            return cache.incr(failure_key)
        except ValueError:
            # The counter may have expired between add() and incr().
            if cache.add(
                failure_key,
                1,
                timeout=LOGIN_FAILURE_WINDOW_SECONDS,
            ):
                return 1

            return cache.incr(failure_key)

    count = _cache_operation(increment_counter)

    if count < LOGIN_FAILURE_LIMIT:
        return 0

    cooldown_until = time.time() + LOGIN_COOLDOWN_SECONDS

    _cache_operation(
        lambda: cache.set(
            cooldown_key,
            cooldown_until,
            timeout=LOGIN_COOLDOWN_SECONDS,
        )
    )

    return LOGIN_COOLDOWN_SECONDS


def clear_login_failures(email, ip_address):
    failure_key, cooldown_key = _cache_keys(email, ip_address)

    _cache_operation(
        lambda: cache.delete_many([failure_key, cooldown_key])
    )
