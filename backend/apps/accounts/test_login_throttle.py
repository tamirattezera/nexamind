from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from .login_throttle import (
    LOGIN_COOLDOWN_SECONDS,
    LOGIN_FAILURE_LIMIT,
    LoginProtectionUnavailable,
    clear_login_failures,
    get_login_cooldown,
    record_failed_login,
)


class LoginThrottleServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.email = "User@Example.com"
        self.ip_address = "192.0.2.10"

    def tearDown(self):
        cache.clear()

    def test_first_four_failures_do_not_activate_cooldown(self):
        for expected_count in range(1, LOGIN_FAILURE_LIMIT):
            result = record_failed_login(self.email, self.ip_address)
            self.assertEqual(result, 0)
            self.assertEqual(
                get_login_cooldown(self.email, self.ip_address),
                0,
            )

    def test_fifth_failure_activates_cooldown(self):
        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            record_failed_login(self.email, self.ip_address)

        result = record_failed_login(self.email, self.ip_address)

        self.assertEqual(result, LOGIN_COOLDOWN_SECONDS)
        self.assertGreater(
            get_login_cooldown(self.email, self.ip_address),
            0,
        )

    def test_email_normalization_is_consistent(self):
        for _ in range(LOGIN_FAILURE_LIMIT):
            record_failed_login(self.email, self.ip_address)

        self.assertGreater(
            get_login_cooldown(" user@example.COM ", self.ip_address),
            0,
        )

    def test_different_ip_has_independent_counter(self):
        for _ in range(LOGIN_FAILURE_LIMIT):
            record_failed_login(self.email, self.ip_address)

        self.assertEqual(
            get_login_cooldown(self.email, "192.0.2.11"),
            0,
        )

    def test_different_email_has_independent_counter(self):
        for _ in range(LOGIN_FAILURE_LIMIT):
            record_failed_login(self.email, self.ip_address)

        self.assertEqual(
            get_login_cooldown("other@example.com", self.ip_address),
            0,
        )

    def test_successful_login_clears_failure_counter(self):
        for _ in range(LOGIN_FAILURE_LIMIT):
            record_failed_login(self.email, self.ip_address)

        clear_login_failures(self.email, self.ip_address)

        self.assertEqual(
            get_login_cooldown(self.email, self.ip_address),
            0,
        )

        self.assertEqual(
            record_failed_login(self.email, self.ip_address),
            0,
        )

    def test_expired_cooldown_is_not_active(self):
        with patch(
            "apps.accounts.login_throttle.time.time",
            return_value=1000,
        ):
            for _ in range(LOGIN_FAILURE_LIMIT):
                record_failed_login(self.email, self.ip_address)

        with patch(
            "apps.accounts.login_throttle.time.time",
            return_value=1000 + LOGIN_COOLDOWN_SECONDS + 1,
        ):
            self.assertEqual(
                get_login_cooldown(self.email, self.ip_address),
                0,
            )

    def test_cache_failure_fails_closed(self):
        with patch(
            "apps.accounts.login_throttle.cache.get",
            side_effect=ConnectionError("cache unavailable"),
        ):
            with self.assertRaises(LoginProtectionUnavailable):
                get_login_cooldown(self.email, self.ip_address)

    def test_invalid_cooldown_value_fails_closed(self):
        from .login_throttle import _cache_keys

        _, cooldown_key = _cache_keys(self.email, self.ip_address)
        cache.set(cooldown_key, "not-a-timestamp", timeout=900)

        with self.assertRaises(LoginProtectionUnavailable):
            get_login_cooldown(self.email, self.ip_address)
