from django.test import SimpleTestCase, override_settings

from .serializers import SendMessageSerializer


class SendMessageSerializerTests(SimpleTestCase):
    @override_settings(CHAT_MAX_MESSAGE_LENGTH=10000)
    def test_accepts_message_within_configured_limit(self):
        content = "A" * 10000
        serializer = SendMessageSerializer(data={"content": content})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["content"], content)

    @override_settings(CHAT_MAX_MESSAGE_LENGTH=10000)
    def test_rejects_message_exceeding_configured_limit(self):
        content = "A" * 10001
        serializer = SendMessageSerializer(data={"content": content})

        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)

    @override_settings(CHAT_MAX_MESSAGE_LENGTH=100)
    def test_uses_configured_limit_instead_of_hardcoded_limit(self):
        content = "A" * 101
        serializer = SendMessageSerializer(data={"content": content})

        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)

    def test_trims_leading_and_trailing_whitespace(self):
        serializer = SendMessageSerializer(data={"content": "  Hello NexaMind  "})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["content"], "Hello NexaMind")

    def test_rejects_whitespace_only_content(self):
        serializer = SendMessageSerializer(data={"content": "   "})

        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)
