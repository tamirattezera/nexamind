from dataclasses import FrozenInstanceError

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .config import (
    ConversationContextConfig,
    get_conversation_context_config,
)


class ConversationContextConfigTests(SimpleTestCase):
    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=32768)
    def test_returns_configured_context_budget(self):
        config = get_conversation_context_config()

        self.assertIsInstance(config, ConversationContextConfig)
        self.assertEqual(config.max_input_tokens, 32768)

    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=65536)
    def test_accepts_a_different_positive_budget(self):
        config = get_conversation_context_config()

        self.assertEqual(config.max_input_tokens, 65536)

    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=0)
    def test_rejects_zero_context_budget(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHAT_CONTEXT_MAX_INPUT_TOKENS must be greater than zero.",
        ):
            get_conversation_context_config()

    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=-1)
    def test_rejects_negative_context_budget(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHAT_CONTEXT_MAX_INPUT_TOKENS must be greater than zero.",
        ):
            get_conversation_context_config()

    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=32768)
    def test_configuration_is_immutable(self):
        config = get_conversation_context_config()

        with self.assertRaises(FrozenInstanceError):
            config.max_input_tokens = 65536
