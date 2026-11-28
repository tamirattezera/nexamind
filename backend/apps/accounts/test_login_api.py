from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from .login_throttle import LOGIN_FAILURE_LIMIT

User = get_user_model()


class LoginThrottleAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="login@example.com",
            password="StrongPassword123!",
        )
        self.url = "/api/v1/auth/login/"
        self.ip = "192.0.2.10"

    def tearDown(self):
        cache.clear()

    def login(self, email=None, password="WrongPassword123!", ip=None):
        return self.client.post(
            self.url,
            {
                "email": email or self.user.email,
                "password": password,
            },
            format="json",
            REMOTE_ADDR=ip or self.ip,
        )

    def test_first_four_failures_return_401_and_fifth_returns_429(self):
        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            self.assertEqual(self.login().status_code, 401)

        response = self.login()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(int(response["Retry-After"]), 900)

    def test_active_cooldown_blocks_correct_credentials(self):
        for _ in range(LOGIN_FAILURE_LIMIT):
            self.login()

        response = self.login(password="StrongPassword123!")

        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_successful_login_clears_failure_counter(self):
        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            self.login()

        response = self.login(password="StrongPassword123!")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            self.assertEqual(self.login().status_code, 401)

        self.assertEqual(self.login().status_code, 429)

    def test_malformed_requests_do_not_count_as_failed_logins(self):
        for _ in range(5):
            response = self.client.post(
                self.url,
                {"email": self.user.email},
                format="json",
                REMOTE_ADDR=self.ip,
            )
            self.assertEqual(response.status_code, 400)

        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            self.assertEqual(self.login().status_code, 401)

        self.assertEqual(self.login().status_code, 429)

    def test_unknown_email_and_wrong_password_have_same_response(self):
        wrong_password = self.login()
        unknown_email = self.login(email="unknown@example.com")

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_email.status_code, 401)
        self.assertEqual(wrong_password.data, unknown_email.data)

    def test_failure_counters_are_separate_per_ip(self):
        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            self.login(ip="192.0.2.10")

        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            self.assertEqual(
                self.login(ip="192.0.2.11").status_code,
                401,
            )

        self.assertEqual(self.login(ip="192.0.2.10").status_code, 429)

    def test_cache_unavailable_returns_503(self):
        from unittest.mock import patch

        with patch(
            "apps.accounts.login_throttle.cache.get",
            side_effect=ConnectionError("cache unavailable"),
        ):
            response = self.login()

        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.data)
