from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.ai.config import GeminiConfig, get_gemini_config


@override_settings(
    GEMINI_API_KEY="test-api-key",
    GEMINI_MODEL="gemini-3.8-flash",
    GEMINI_THINKING_LEVEL="LOW",
    GEMINI_MAX_OUTPUT_TOKENS=8192,
    GEMINI_TIMEOUT_MS=60000,
)
class GeminiConfigTests(SimpleTestCase):
    def test_returns_validated_configuration(self):
        config = get_gemini_config()

        self.assertIsInstance(config, GeminiConfig)
        self.assertEqual(config.api_key, "test-api-key")
        self.assertEqual(config.model, "gemini-3.8-flash")
        self.assertEqual(config.thinking_level, "LOW")
        self.assertEqual(config.max_output_tokens, 8192)
        self.assertEqual(config.timeout_ms, 60000)

    def test_strips_api_key_and_model_whitespace(self):
        with self.settings(
            GEMINI_API_KEY="  test-api-key  ",
            GEMINI_MODEL="  gemini-3.8-flash  ",
        ):
            config = get_gemini_config()

        self.assertEqual(config.api_key, "test-api-key")
        self.assertEqual(config.model, "gemini-3.8-flash")

    def test_rejects_missing_api_key(self):
        with self.settings(GEMINI_API_KEY=""):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "GEMINI_API_KEY must be configured.",
            ):
                get_gemini_config()

    def test_rejects_empty_model(self):
        with self.settings(GEMINI_MODEL="   "):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "GEMINI_MODEL must not be empty.",
            ):
                get_gemini_config()

    def test_rejects_unsupported_thinking_level(self):
        with self.settings(GEMINI_THINKING_LEVEL="MINIMAL"):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "GEMINI_THINKING_LEVEL must be LOW, MEDIUM, or HIGH.",
            ):
                get_gemini_config()

    def test_rejects_nonpositive_output_token_limit(self):
        with self.settings(GEMINI_MAX_OUTPUT_TOKENS=0):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "GEMINI_MAX_OUTPUT_TOKENS must be greater than zero.",
            ):
                get_gemini_config()

    def test_rejects_nonpositive_timeout(self):
        with self.settings(GEMINI_TIMEOUT_MS=0):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "GEMINI_TIMEOUT_MS must be greater than zero.",
            ):
                get_gemini_config()
