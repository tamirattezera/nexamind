from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.contracts import (
    ConversationMessage,
    GenerationRequest,
    GenerationResult,
)
from apps.ai.providers.gemini import ProviderTimeoutError
from apps.ai.services import generate_response

from apps.ai.contracts import TokenCountRequest, TokenCountResult
from apps.ai.services import count_tokens
from apps.ai.config import GeminiConfig


class GenerateResponseServiceTests(SimpleTestCase):
    def setUp(self):
        self.request = GenerationRequest(
            messages=(ConversationMessage(role="user", content="Hello"),),
            system_instruction="You are NexaMind.",
        )

        self.result = GenerationResult(
            text="Hello!",
            model_name="gemini-3.8-flash",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            thinking_tokens=2,
            finish_reason="STOP",
            response_id="response-123",
        )

    @patch("apps.ai.services.GeminiProvider")
    def test_delegates_generation_and_returns_result(self, provider_class):
        provider = provider_class.return_value
        provider.generate.return_value = self.result

        result = generate_response(self.request)

        provider_class.assert_called_once_with()
        provider.generate.assert_called_once_with(self.request)
        provider.close.assert_called_once_with()
        self.assertEqual(result, self.result)

    @patch("apps.ai.services.GeminiProvider")
    def test_uses_explicit_generation_configuration(self, provider_class):
        config = GeminiConfig(
            api_key="test-api-key",
            model="gemini-test-model",
            thinking_level="HIGH",
            max_output_tokens=4096,
            timeout_ms=30000,
        )

        provider = provider_class.return_value
        provider.generate.return_value = self.result

        result = generate_response(self.request, config=config)

        provider_class.assert_called_once_with(config=config)
        provider.generate.assert_called_once_with(self.request)
        provider.close.assert_called_once_with()
        self.assertEqual(result, self.result)


    @patch("apps.ai.services.GeminiProvider")
    def test_closes_provider_when_generation_fails(self, provider_class):
        provider = provider_class.return_value
        provider.generate.side_effect = ProviderTimeoutError(
            "The Gemini request timed out."
        )

        with self.assertRaises(ProviderTimeoutError):
            generate_response(self.request)

        provider.close.assert_called_once_with()

    @patch("apps.ai.services.GeminiProvider")
    def test_propagates_provider_error(self, provider_class):
        provider = provider_class.return_value
        error = RuntimeError("Unexpected provider failure")
        provider.generate.side_effect = error

        with self.assertRaises(RuntimeError) as context:
            generate_response(self.request)

        self.assertIs(context.exception, error)
        provider.close.assert_called_once_with()


class CountTokensServiceTests(SimpleTestCase):
    def setUp(self):
        self.request = TokenCountRequest(
            messages=(ConversationMessage(role="user", content="Hello"),),
            system_instruction="You are NexaMind.",
        )

        self.result = TokenCountResult(total_tokens=42)

    @patch("apps.ai.services.GeminiProvider")
    def test_delegates_token_count_and_returns_result(self, provider_class):
        provider = provider_class.return_value
        provider.count_tokens.return_value = self.result

        result = count_tokens(self.request)

        provider_class.assert_called_once_with()
        provider.count_tokens.assert_called_once_with(self.request)
        provider.close.assert_called_once_with()
        self.assertEqual(result, self.result)

    @patch("apps.ai.services.GeminiProvider")
    def test_closes_provider_when_token_count_fails(self, provider_class):
        provider = provider_class.return_value
        error = ProviderTimeoutError("The request timed out.")
        provider.count_tokens.side_effect = error

        with self.assertRaises(ProviderTimeoutError) as context:
            count_tokens(self.request)

        self.assertIs(context.exception, error)
        provider.close.assert_called_once_with()


    @patch("apps.ai.services.GeminiProvider")
    def test_uses_explicit_configuration(self, provider_class):
        config = GeminiConfig(
            api_key="test-api-key",
            model="gemini-3.8-flash",
            thinking_level="LOW",
            max_output_tokens=8192,
            timeout_ms=60000,
        )

        provider = provider_class.return_value
        provider.count_tokens.return_value = self.result

        result = count_tokens(self.request, config=config)

        provider_class.assert_called_once_with(config=config)
        provider.count_tokens.assert_called_once_with(self.request)
        provider.close.assert_called_once_with()
        self.assertEqual(result, self.result)
