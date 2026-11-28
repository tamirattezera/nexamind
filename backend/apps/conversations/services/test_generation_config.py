from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .generation_config import get_generation_rate_limit_config


class GenerationRateLimitConfigTests(SimpleTestCase):
    @override_settings(
        CHAT_GENERATION_RATE_LIMIT=10,
        CHAT_GENERATION_RATE_WINDOW_SECONDS=60,
    )
    def test_rejects_non_integer_policy_values(self):
        invalid_values = (True, "10", 1.5, None)

        for setting in (
            "CHAT_GENERATION_RATE_LIMIT",
            "CHAT_GENERATION_RATE_WINDOW_SECONDS",
        ):
            for value in invalid_values:
                with self.subTest(setting=setting, value=value):
                    with override_settings(**{setting: value}):
                        with self.assertRaises(ImproperlyConfigured):
                            get_generation_rate_limit_config()

    def test_returns_default_policy_values(self):
        config = get_generation_rate_limit_config()

        self.assertEqual(config.limit, 10)
        self.assertEqual(config.window_seconds, 60)

    @override_settings(
        CHAT_GENERATION_RATE_LIMIT=5,
        CHAT_GENERATION_RATE_WINDOW_SECONDS=30,
    )
    def test_accepts_custom_positive_values(self):
        config = get_generation_rate_limit_config()

        self.assertEqual(config.limit, 5)
        self.assertEqual(config.window_seconds, 30)

    @override_settings(CHAT_GENERATION_RATE_LIMIT=0)
    def test_rejects_zero_limit(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHAT_GENERATION_RATE_LIMIT must be greater than zero.",
        ):
            get_generation_rate_limit_config()

    @override_settings(CHAT_GENERATION_RATE_LIMIT=-1)
    def test_rejects_negative_limit(self):
        with self.assertRaises(ImproperlyConfigured):
            get_generation_rate_limit_config()

    @override_settings(CHAT_GENERATION_RATE_WINDOW_SECONDS=0)
    def test_rejects_zero_window(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHAT_GENERATION_RATE_WINDOW_SECONDS must be greater than zero.",
        ):
            get_generation_rate_limit_config()

    @override_settings(CHAT_GENERATION_RATE_WINDOW_SECONDS=-1)
    def test_rejects_negative_window(self):
        with self.assertRaises(ImproperlyConfigured):
            get_generation_rate_limit_config()
