from dataclasses import FrozenInstanceError

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .message_config import (
    ConversationMessageConfig,
    get_conversation_message_config,
)


class ConversationMessageConfigTests(SimpleTestCase):
    @override_settings(CHAT_MAX_MESSAGE_LENGTH=10000)
    def test_returns_configured_message_length(self):
        config = get_conversation_message_config()

        self.assertIsInstance(config, ConversationMessageConfig)
        self.assertEqual(config.max_message_length, 10000)

    @override_settings(CHAT_MAX_MESSAGE_LENGTH=5000)
    def test_accepts_a_different_positive_limit(self):
        config = get_conversation_message_config()

        self.assertEqual(config.max_message_length, 5000)

    @override_settings(CHAT_MAX_MESSAGE_LENGTH=0)
    def test_rejects_zero_message_length(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHAT_MAX_MESSAGE_LENGTH must be greater than zero.",
        ):
            get_conversation_message_config()

    @override_settings(CHAT_MAX_MESSAGE_LENGTH=-1)
    def test_rejects_negative_message_length(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHAT_MAX_MESSAGE_LENGTH must be greater than zero.",
        ):
            get_conversation_message_config()

    @override_settings(CHAT_MAX_MESSAGE_LENGTH=10000)
    def test_configuration_is_immutable(self):
        config = get_conversation_message_config()

        with self.assertRaises(FrozenInstanceError):
            config.max_message_length = 5000
