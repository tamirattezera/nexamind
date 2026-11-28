from unittest.mock import patch

from django.core.checks import Error
from django.test import SimpleTestCase, override_settings

from .checks import check_production_cache


REDIS_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}


class ProductionCacheCheckTests(SimpleTestCase):

    @override_settings(DEBUG=True, IS_PRODUCTION=False)
    def test_development_skips_redis_check(self):
        self.assertEqual(check_production_cache(None), [])

    @override_settings(
        DEBUG=False,
        IS_PRODUCTION=True,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache",
            }
        },
    )
    def test_production_rejects_non_redis_backend(self):
        errors = check_production_cache(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "accounts.E001")

    @override_settings(DEBUG=False, IS_PRODUCTION=True, CACHES=REDIS_CACHES)
    @patch("apps.accounts.checks.cache.delete")
    @patch("apps.accounts.checks.cache.get")
    @patch("apps.accounts.checks.cache.set")
    def test_reachable_redis_passes(self, mock_set, mock_get, mock_delete):
        mock_get.side_effect = lambda key: mock_set.call_args.args[1]

        errors = check_production_cache(None)

        self.assertEqual(errors, [])
        mock_set.assert_called_once()
        mock_get.assert_called_once()
        mock_delete.assert_called_once_with(mock_set.call_args.args[0])

    @override_settings(DEBUG=False, IS_PRODUCTION=True, CACHES=REDIS_CACHES)
    @patch(
        "apps.accounts.checks.cache.set",
        side_effect=ConnectionError("Redis unavailable"),
    )
    def test_unavailable_redis_fails_check(self, mock_set):
        errors = check_production_cache(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "accounts.E003")

    @override_settings(DEBUG=False, IS_PRODUCTION=True, CACHES=REDIS_CACHES)
    @patch("apps.accounts.checks.cache.delete")
    @patch("apps.accounts.checks.cache.get", return_value="wrong-value")
    @patch("apps.accounts.checks.cache.set")
    def test_failed_readback_fails_check(
        self, mock_set, mock_get, mock_delete
    ):
        errors = check_production_cache(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "accounts.E002")
        mock_delete.assert_called_once()
