from unittest.mock import Mock

import httpx2
from django.test import SimpleTestCase
from google.genai import errors, types

from apps.ai.config import GeminiConfig
from apps.ai.contracts import (
    ConversationMessage,
    GenerationRequest,
    TokenCountRequest,
    TokenCountResult,
)
from apps.ai.providers.gemini import (
    GeminiProvider,
    ProviderBlockedError,
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    build_gemini_contents,
    normalize_gemini_response,
)


class GeminiContentMappingTests(SimpleTestCase):
    def test_maps_user_and_assistant_roles(self):
        messages = (
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi"),
        )

        contents = build_gemini_contents(messages)

        self.assertEqual(len(contents), 2)
        self.assertEqual(contents[0].role, "user")
        self.assertEqual(contents[1].role, "model")
        self.assertEqual(contents[0].parts[0].text, "Hello")
        self.assertEqual(contents[1].parts[0].text, "Hi")


class GeminiResponseNormalizationTests(SimpleTestCase):
    def make_response(self, **overrides):
        data = {
            "model_version": "gemini-3.8-flash",
            "response_id": "response-123",
            "candidates": [
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(text="Internal reasoning", thought=True),
                            types.Part(text="Hello from Gemini"),
                        ],
                    ),
                    finish_reason=types.FinishReason.STOP,
                )
            ],
            "usage_metadata": types.GenerateContentResponseUsageMetadata(
                prompt_token_count=100,
                candidates_token_count=20,
                total_token_count=130,
                thoughts_token_count=10,
            ),
        }
        data.update(overrides)
        return types.GenerateContentResponse(**data)

    def test_normalizes_successful_response(self):
        result = normalize_gemini_response(
            self.make_response(),
            "configured-model",
        )

        self.assertEqual(result.text, "Hello from Gemini")
        self.assertEqual(result.model_name, "gemini-3.8-flash")
        self.assertEqual(result.input_tokens, 100)
        self.assertEqual(result.output_tokens, 20)
        self.assertEqual(result.total_tokens, 130)
        self.assertEqual(result.thinking_tokens, 10)
        self.assertEqual(result.finish_reason, "STOP")
        self.assertEqual(result.response_id, "response-123")

    def test_uses_configured_model_when_response_model_missing(self):
        response = self.make_response(model_version=None)

        result = normalize_gemini_response(response, "configured-model")

        self.assertEqual(result.model_name, "configured-model")

    def test_preserves_max_tokens_finish_reason(self):
        response = self.make_response(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="Partial answer")],
                    ),
                    finish_reason=types.FinishReason.MAX_TOKENS,
                )
            ]
        )

        result = normalize_gemini_response(response, "configured-model")

        self.assertEqual(result.text, "Partial answer")
        self.assertEqual(result.finish_reason, "MAX_TOKENS")

    def test_rejects_missing_candidates(self):
        response = self.make_response(candidates=[])

        with self.assertRaises(ProviderResponseError):
            normalize_gemini_response(response, "configured-model")

    def test_rejects_missing_candidate_content(self):
        response = self.make_response(
            candidates=[
                types.Candidate(finish_reason=types.FinishReason.STOP)
            ]
        )

        with self.assertRaises(ProviderResponseError):
            normalize_gemini_response(response, "configured-model")

    def test_rejects_thinking_without_visible_text(self):
        response = self.make_response(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(text="Internal reasoning", thought=True)
                        ],
                    ),
                    finish_reason=types.FinishReason.STOP,
                )
            ]
        )

        with self.assertRaises(ProviderResponseError):
            normalize_gemini_response(response, "configured-model")

    def test_rejects_blocked_prompt(self):
        response = self.make_response(
            prompt_feedback=types.GenerateContentResponsePromptFeedback(
                block_reason=types.BlockedReason.SAFETY,
            )
        )

        with self.assertRaises(ProviderBlockedError):
            normalize_gemini_response(response, "configured-model")

    def test_rejects_safety_finish_reason(self):
        response = self.make_response(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="")],
                    ),
                    finish_reason=types.FinishReason.SAFETY,
                )
            ]
        )

        with self.assertRaises(ProviderBlockedError):
            normalize_gemini_response(response, "configured-model")


class GeminiProviderTests(SimpleTestCase):
    def setUp(self):
        self.config = GeminiConfig(
            api_key="test-key",
            model="gemini-3.8-flash",
            thinking_level="LOW",
            max_output_tokens=8192,
            timeout_ms=60000,
        )

        self.request = GenerationRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
            ),
            system_instruction="You are NexaMind.",
        )

        self.response = types.GenerateContentResponse(
            model_version="gemini-3.8-flash",
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="Hello from Gemini")],
                    ),
                    finish_reason=types.FinishReason.STOP,
                )
            ],
        )

        self.client = Mock()
        self.client.models.generate_content.return_value = self.response

        self.provider = GeminiProvider(
            config=self.config,
            client=self.client,
        )

    def test_generates_with_approved_configuration(self):
        result = self.provider.generate(self.request)

        self.assertEqual(result.text, "Hello from Gemini")

        self.client.models.generate_content.assert_called_once()

        call = self.client.models.generate_content.call_args
        self.assertEqual(call.kwargs["model"], "gemini-3.8-flash")
        self.assertEqual(call.kwargs["contents"][0].role, "user")

        generation_config = call.kwargs["config"]
        self.assertEqual(generation_config.system_instruction, "You are NexaMind.")
        self.assertEqual(generation_config.max_output_tokens, self.config.max_output_tokens)
        self.assertEqual(
            generation_config.thinking_config.thinking_level,
            self.config.thinking_level,
        )

    def test_translates_timeout(self):
        self.client.models.generate_content.side_effect = (
            httpx2.ReadTimeout("timeout")
        )

        with self.assertRaises(ProviderTimeoutError):
            self.provider.generate(self.request)

    def test_translates_connection_error(self):
        self.client.models.generate_content.side_effect = (
            httpx2.ConnectError("connection failed")
        )

        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)

    def test_translates_gemini_api_error(self):
        self.client.models.generate_content.side_effect = errors.APIError(
            500,
            {"message": "internal provider error"},
        )

        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)

    def test_counts_tokens_with_system_instruction_and_mapped_messages(self):
        self.client.models.count_tokens.return_value = Mock(total_tokens=42)

        request = TokenCountRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
                ConversationMessage(role="assistant", content="Hi"),
            ),
            system_instruction="You are NexaMind.",
        )

        result = self.provider.count_tokens(request)

        self.assertEqual(result, TokenCountResult(total_tokens=42))

        self.client.models.count_tokens.assert_called_once()
        call = self.client.models.count_tokens.call_args

        self.assertEqual(call.kwargs["model"], "gemini-3.8-flash")
        self.assertEqual(
            [item.role for item in call.kwargs["contents"]],
            ["user", "model"],
        )
        self.assertEqual(
            call.kwargs["config"].system_instruction,
            "You are NexaMind.",
        )

    def test_translates_token_count_timeout(self):
        self.client.models.count_tokens.side_effect = (
            httpx2.ReadTimeout("timeout")
        )

        request = TokenCountRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
            ),
            system_instruction="You are NexaMind.",
        )

        with self.assertRaises(ProviderTimeoutError):
            self.provider.count_tokens(request)

    def test_translates_token_count_connection_error(self):
        self.client.models.count_tokens.side_effect = (
            httpx2.ConnectError("connection failed")
        )

        request = TokenCountRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
            ),
            system_instruction="You are NexaMind.",
        )

        with self.assertRaises(ProviderError):
            self.provider.count_tokens(request)

    def test_translates_token_count_api_error(self):
        self.client.models.count_tokens.side_effect = errors.APIError(
            500,
            {"message": "internal provider error"},
        )

        request = TokenCountRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
            ),
            system_instruction="You are NexaMind.",
        )

        with self.assertRaises(ProviderError):
            self.provider.count_tokens(request)

    def test_rejects_missing_token_count(self):
        self.client.models.count_tokens.return_value = Mock(
            total_tokens=None,
        )

        request = TokenCountRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
            ),
            system_instruction="You are NexaMind.",
        )

        with self.assertRaises(ProviderResponseError):
            self.provider.count_tokens(request)

    def test_rejects_negative_token_count(self):
        self.client.models.count_tokens.return_value = Mock(
            total_tokens=-1,
        )

        request = TokenCountRequest(
            messages=(
                ConversationMessage(role="user", content="Hello"),
            ),
            system_instruction="You are NexaMind.",
        )

        with self.assertRaises(ProviderResponseError):
            self.provider.count_tokens(request)

    def test_does_not_close_injected_client(self):
        self.provider.close()

        self.client.close.assert_not_called()
