from types import SimpleNamespace

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.ai.config import GeminiConfig
from apps.conversations.services.execution_config import (
    reconstruct_generation_config,
)


class ReconstructGenerationConfigTests(SimpleTestCase):
    def setUp(self):
        self.metadata = {
            "schema_version": 1,
            "provider": "gemini",
            "requested_model": "gemini-accepted-model",
            "thinking_level": "HIGH",
        }
        self.chat_turn = SimpleNamespace(
            generation_metadata=self.metadata.copy(),
            max_output_tokens=4096,
        )

    @override_settings(
        GEMINI_API_KEY=" current-server-secret ",
        GEMINI_TIMEOUT_MS=45000,
        GEMINI_MODEL="different-current-model",
        GEMINI_THINKING_LEVEL="LOW",
        GEMINI_MAX_OUTPUT_TOKENS=8192,
    )
    def test_reconstructs_persisted_choices_and_current_operational_settings(self):
        config = reconstruct_generation_config(self.chat_turn)

        self.assertEqual(
            config,
            GeminiConfig(
                api_key="current-server-secret",
                model="gemini-accepted-model",
                thinking_level="HIGH",
                max_output_tokens=4096,
                timeout_ms=45000,
            ),
        )

    def test_rejects_missing_metadata(self):
        self.chat_turn.generation_metadata = None

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "ChatTurn generation metadata has an invalid structure.",
        ):
            reconstruct_generation_config(self.chat_turn)

    def test_rejects_metadata_with_missing_or_unknown_keys(self):
        self.chat_turn.generation_metadata.pop("thinking_level")

        with self.assertRaises(ImproperlyConfigured):
            reconstruct_generation_config(self.chat_turn)

        self.chat_turn.generation_metadata = {
            **self.metadata,
            "unexpected": "value",
        }

        with self.assertRaises(ImproperlyConfigured):
            reconstruct_generation_config(self.chat_turn)

    def test_rejects_unsupported_schema_version(self):
        self.chat_turn.generation_metadata["schema_version"] = 2

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "ChatTurn generation metadata has an unsupported schema version.",
        ):
            reconstruct_generation_config(self.chat_turn)

    def test_rejects_boolean_schema_version(self):
        self.chat_turn.generation_metadata["schema_version"] = True

        with self.assertRaises(ImproperlyConfigured):
            reconstruct_generation_config(self.chat_turn)

    def test_rejects_unsupported_provider(self):
        self.chat_turn.generation_metadata["provider"] = "other"

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "ChatTurn generation metadata specifies an unsupported provider.",
        ):
            reconstruct_generation_config(self.chat_turn)

    def test_rejects_missing_or_invalid_model(self):
        for model in ("", "   ", None, 123, " gemini-model "):
            with self.subTest(model=model):
                self.chat_turn.generation_metadata["requested_model"] = model

                with self.assertRaises(ImproperlyConfigured):
                    reconstruct_generation_config(self.chat_turn)

    def test_rejects_unsupported_thinking_level(self):
        for level in ("", "INVALID", "low", None, 123):
            with self.subTest(level=level):
                self.chat_turn.generation_metadata["thinking_level"] = level

                with self.assertRaises(ImproperlyConfigured):
                    reconstruct_generation_config(self.chat_turn)

    def test_rejects_missing_or_invalid_output_token_limit(self):
        for value in (None, 0, -1, True, "4096", 4096.0):
            with self.subTest(value=value):
                self.chat_turn.max_output_tokens = value

                with self.assertRaises(ImproperlyConfigured):
                    reconstruct_generation_config(self.chat_turn)

    @override_settings(GEMINI_API_KEY="")
    def test_rejects_missing_current_api_key(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "GEMINI_API_KEY must be configured.",
        ):
            reconstruct_generation_config(self.chat_turn)

    @override_settings(GEMINI_API_KEY="test-api-key", GEMINI_TIMEOUT_MS=0)
    def test_rejects_zero_current_timeout(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "GEMINI_TIMEOUT_MS must be a positive integer.",
        ):
            reconstruct_generation_config(self.chat_turn)

    @override_settings(GEMINI_API_KEY="test-api-key", GEMINI_TIMEOUT_MS=-1)
    def test_rejects_negative_current_timeout(self):
        with self.assertRaises(ImproperlyConfigured):
            reconstruct_generation_config(self.chat_turn)

    @override_settings(GEMINI_API_KEY="test-api-key", GEMINI_TIMEOUT_MS=True)
    def test_rejects_boolean_current_timeout(self):
        with self.assertRaises(ImproperlyConfigured):
            reconstruct_generation_config(self.chat_turn)
