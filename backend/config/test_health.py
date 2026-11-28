import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from django.test import Client, SimpleTestCase, override_settings


class HealthCheckTests(SimpleTestCase):
    def setUp(self):
        self._settings_override = override_settings(ALLOWED_HOSTS=["testserver"])
        self._settings_override.enable()
        self.addCleanup(self._settings_override.disable)
        self.client = Client()

    def test_liveness_succeeds_without_checking_dependencies(self):
        with (
            patch("config.health.connection") as database,
            patch("config.health.cache.get") as cache_get,
        ):
            response = self.client.get("/api/v1/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        database.assert_not_called()
        cache_get.assert_not_called()

    def test_readiness_succeeds_when_dependencies_are_available(self):
        cursor = MagicMock()
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = cursor

        with (
            patch(
                "config.health.transaction.atomic"
            ) as atomic,
            patch(
                "config.health.connection",
                cursor=MagicMock(return_value=cursor_context),
            ),
            patch("config.health.cache.get", return_value=None) as cache_get,
            patch(
                "config.health.settings.HEALTH_CHECK_DB_STATEMENT_TIMEOUT_MS",
                2000,
            ),
        ):
            response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        atomic.assert_called_once_with(using="default")
        cursor.execute.assert_has_calls([
            call(
                "SELECT set_config('statement_timeout', %s, true)",
                ["2000ms"],
            ),
            call("SELECT 1"),
        ])
        cursor.fetchone.assert_called_once()
        cache_get.assert_called_once_with("nexamind:health-check")

    def test_database_failure_returns_generic_unavailable_response(self):
        with (
            patch("config.health.transaction.atomic"),
            patch(
                "config.health.connection",
                cursor=MagicMock(
                    side_effect=ConnectionError("database credentials leaked")
                ),
            ),
            patch("config.health.cache.get") as cache_get,
        ):
            response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn(b"credentials", response.content)
        cache_get.assert_not_called()

    def test_cache_failure_returns_generic_unavailable_response(self):
        with (
            patch("config.health.transaction.atomic"),
            patch("config.health.connection"),
            patch(
                "config.health.cache.get",
                side_effect=ConnectionError("redis internal details"),
            ),
        ):
            response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn(b"redis", response.content.lower())

    def test_liveness_only_accepts_get(self):
        response = self.client.post("/api/v1/health/live/")

        self.assertEqual(response.status_code, 405)

    def test_readiness_only_accepts_get(self):
        response = self.client.post("/api/v1/health/")

        self.assertEqual(response.status_code, 405)


class HealthTimeoutConfigurationTests(SimpleTestCase):
    def test_non_positive_statement_timeout_prevents_startup(self):
        backend_dir = Path(__file__).resolve().parent.parent

        for timeout in ("0", "-1"):
            with self.subTest(timeout=timeout):
                environment = os.environ.copy()
                environment["HEALTH_CHECK_DB_STATEMENT_TIMEOUT_MS"] = timeout

                result = subprocess.run(
                    [sys.executable, "manage.py", "check"],
                    cwd=backend_dir,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "HEALTH_CHECK_DB_STATEMENT_TIMEOUT_MS must be greater than zero.",
                    result.stderr,
                )
