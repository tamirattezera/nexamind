import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from django.test.utils import CaptureQueriesContext

from apps.ai.contracts import TokenCountResult
from apps.ai.providers.gemini import ProviderTimeoutError
from apps.conversations.models import ChatTurn, Conversation, Message

from .builder import prepare_conversation_context
from .exceptions import ContextLimitExceeded, ContextUnavailable
from ..instructions.platform import (
    PLATFORM_INSTRUCTION_VERSION,
    PLATFORM_SYSTEM_INSTRUCTION,
)
from apps.ai.config import GeminiConfig

User = get_user_model()


class PrepareConversationContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="builder@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Context builder tests",
        )

        self.current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        self.generation_config = GeminiConfig(
            api_key="test-api-key",
            model="gemini-3.8-flash",
            thinking_level="LOW",
            max_output_tokens=8192,
            timeout_ms=60000,
        )


    def create_completed_turn(self, content):
        user_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content=f"User: {content}",
        )
        assistant_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content=f"Assistant: {content}",
        )

        ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            idempotency_key=uuid.uuid4(),
            request_hash="a" * 64,
            status=ChatTurn.Status.COMPLETED,
            completed_at=timezone.now(),
            system_instruction_version="v1",
            system_instruction_snapshot="Previous instruction",
        )

        return user_message, assistant_message

    @patch("apps.conversations.context.builder.count_tokens")
    def test_accepts_unsaved_current_user_message(self, count_tokens):
        count_tokens.return_value = TokenCountResult(total_tokens=12)

        prepared = prepare_conversation_context(
            conversation=self.conversation,
            current_user_message=self.current_message,
            generation_config=self.generation_config,
        )

        self.assertTrue(self.current_message._state.adding)
        self.assertEqual(prepared.current_message_id, self.current_message.id)
        self.assertEqual(
            prepared.messages[-1].content,
            "Current question",
        )
        self.assertEqual(prepared.input_tokens, 12)
        count_tokens.assert_called_once()

    def test_rejects_non_user_current_message(self):
        invalid_message = Message(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="Not a user message",
        )

        with self.assertRaises(ValueError):
            prepare_conversation_context(
                conversation=self.conversation,
                current_user_message=invalid_message,
                generation_config=self.generation_config,
            )

    def test_rejects_message_from_another_conversation(self):
        other_conversation = Conversation.objects.create(
            user=self.user,
            title="Another conversation",
        )
        invalid_message = Message(
            conversation=other_conversation,
            role=Message.Role.USER,
            content="Wrong conversation",
        )

        with self.assertRaises(ValueError):
            prepare_conversation_context(
                conversation=self.conversation,
                current_user_message=invalid_message,
                generation_config=self.generation_config,
            )

    @patch("apps.conversations.context.builder.count_tokens")
    def test_combines_platform_and_custom_instructions(self, count_tokens):
        self.conversation.custom_instructions = "Use concise explanations."
        self.conversation.save(update_fields=["custom_instructions"])
        count_tokens.return_value = TokenCountResult(total_tokens=20)

        prepared = prepare_conversation_context(
            conversation=self.conversation,
            current_user_message=self.current_message,
            generation_config=self.generation_config,
        )

        self.assertEqual(
            prepared.system_instruction,
            (f"{PLATFORM_SYSTEM_INSTRUCTION}\n\n" "Use concise explanations."),
        )
        self.assertEqual(
            prepared.platform_instruction_version,
            PLATFORM_INSTRUCTION_VERSION,
        )
        self.assertEqual(
            prepared.platform_instruction_snapshot,
            PLATFORM_SYSTEM_INSTRUCTION,
        )
        self.assertEqual(
            prepared.custom_instruction_snapshot,
            "Use concise explanations.",
        )

    @patch("apps.conversations.context.builder.count_tokens")
    def test_normalizes_blank_custom_instruction_to_none(self, count_tokens):
        self.conversation.custom_instructions = "  \n  "
        self.conversation.save(update_fields=["custom_instructions"])
        count_tokens.return_value = TokenCountResult(total_tokens=10)

        prepared = prepare_conversation_context(
            conversation=self.conversation,
            current_user_message=self.current_message,
            generation_config=self.generation_config,
        )

        self.assertIsNone(prepared.custom_instruction_snapshot)
        self.assertEqual(
            prepared.system_instruction,
            PLATFORM_SYSTEM_INSTRUCTION,
        )

    @patch("apps.conversations.context.builder.count_tokens")
    def test_preserves_chronological_history_and_current_message_last(
        self,
        count_tokens,
    ):
        first = self.create_completed_turn("first exchange")
        second = self.create_completed_turn("second exchange")
        count_tokens.return_value = TokenCountResult(total_tokens=30)

        prepared = prepare_conversation_context(
            conversation=self.conversation,
            current_user_message=self.current_message,
            generation_config=self.generation_config,
        )

        self.assertEqual(
            prepared.selected_history_message_ids,
            tuple(message.id for message in (*first, *second)),
        )
        self.assertEqual(
            [message.content for message in prepared.messages],
            [
                "User: first exchange",
                "Assistant: first exchange",
                "User: second exchange",
                "Assistant: second exchange",
                "Current question",
            ],
        )

    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=3)
    @patch("apps.conversations.context.builder.count_tokens")
    def test_trims_oldest_complete_exchanges_and_keeps_newest(
        self,
        count_tokens,
    ):
        first = self.create_completed_turn("first exchange")
        second = self.create_completed_turn("second exchange")
        third = self.create_completed_turn("third exchange")

        count_tokens.side_effect = lambda request, *, config: TokenCountResult(
            total_tokens=len(request.messages)
        )

        prepared = prepare_conversation_context(
            conversation=self.conversation,
            current_user_message=self.current_message,
            generation_config=self.generation_config,
        )

        self.assertEqual(
            prepared.selected_history_message_ids,
            tuple(message.id for message in third),
        )
        self.assertEqual(
            [message.content for message in prepared.messages],
            [
                "User: third exchange",
                "Assistant: third exchange",
                "Current question",
            ],
        )
        self.assertEqual(prepared.input_tokens, 3)
        self.assertLessEqual(
            prepared.input_tokens,
            prepared.max_input_tokens,
        )

        # Three historical exchanges should not require a linear
        # token-counting pass over every possible retained suffix.
        self.assertLessEqual(count_tokens.call_count, 4)

        # Verify that binary search tested the mandatory context,
        # the newest one-exchange suffix, and the larger suffix
        # that exceeds the budget.
        self.assertEqual(
            [len(call.args[0].messages) for call in count_tokens.call_args_list],
            [7, 1, 3, 5],
        )

    @override_settings(CHAT_CONTEXT_MAX_INPUT_TOKENS=2)
    @patch("apps.conversations.context.builder.count_tokens")
    def test_raises_when_mandatory_context_exceeds_budget(self, count_tokens):
        count_tokens.return_value = TokenCountResult(total_tokens=3)

        with self.assertRaises(ContextLimitExceeded):
            prepare_conversation_context(
                conversation=self.conversation,
                current_user_message=self.current_message,
                generation_config=self.generation_config,
            )

    @patch("apps.conversations.context.builder.count_tokens")
    def test_translates_provider_failure_to_context_unavailable(
        self,
        count_tokens,
    ):
        error = ProviderTimeoutError("The provider timed out.")
        count_tokens.side_effect = error

        with self.assertRaises(ContextUnavailable) as context:
            prepare_conversation_context(
                conversation=self.conversation,
                current_user_message=self.current_message,
                generation_config=self.generation_config,
            )

        self.assertEqual(
            context.exception.error_code,
            "CHAT_CONTEXT_UNAVAILABLE",
        )
        self.assertIs(context.exception.__cause__, error)
        self.assertNotIn("provider timed out", str(context.exception))

    @patch("apps.conversations.context.builder.count_tokens")
    def test_propagates_unexpected_token_counting_failure(self, count_tokens):
        error = RuntimeError("Unexpected token counting failure")
        count_tokens.side_effect = error

        with self.assertRaises(RuntimeError) as context:
            prepare_conversation_context(
                conversation=self.conversation,
                current_user_message=self.current_message,
                generation_config=self.generation_config,
            )

        self.assertIs(context.exception, error)

    @patch("apps.conversations.context.builder.count_tokens")
    def test_preparing_context_does_not_write_to_database(
        self,
        count_tokens,
    ):
        self.create_completed_turn("existing history")
        count_tokens.return_value = TokenCountResult(total_tokens=20)

        with CaptureQueriesContext(connection) as queries:
            prepared = prepare_conversation_context(
                conversation=self.conversation,
                current_user_message=self.current_message,
                generation_config=self.generation_config,
            )

        write_statements = [
            query["sql"]
            for query in queries.captured_queries
            if query["sql"]
            .lstrip()
            .upper()
            .startswith(("INSERT ", "UPDATE ", "DELETE "))
        ]

        self.assertEqual(write_statements, [])
        self.assertEqual(len(prepared.selected_history_message_ids), 2)
        self.assertTrue(self.current_message._state.adding)


    @patch("apps.conversations.context.builder.count_tokens")
    def test_reuses_explicit_generation_config_for_every_token_count(
        self,
        count_tokens,
    ):
        generation_config = GeminiConfig(
            api_key="test-api-key",
            model="gemini-3.8-flash",
            thinking_level="LOW",
            max_output_tokens=8192,
            timeout_ms=60000,
        )

        count_tokens.side_effect = [
            TokenCountResult(total_tokens=40000),
            TokenCountResult(total_tokens=10),
        ]

        prepared = prepare_conversation_context(
            conversation=self.conversation,
            current_user_message=self.current_message,
            generation_config=generation_config,
        )

        self.assertEqual(prepared.input_tokens, 10)
        self.assertEqual(count_tokens.call_count, 2)

        for call in count_tokens.call_args_list:
            self.assertIs(
                call.kwargs["config"],
                generation_config,
            )
