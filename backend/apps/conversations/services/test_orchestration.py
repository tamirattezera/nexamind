import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ai.config import GeminiConfig
from apps.ai.contracts import ConversationMessage
from apps.conversations.context.contracts import PreparedConversationContext
from apps.conversations.context.exceptions import (
    ContextChanged,
    ContextLimitExceeded,
    ContextSnapshotStale,
    ContextUnavailable,
)
from apps.conversations.idempotency import hash_message_content
from apps.conversations.instructions.platform import (
    PLATFORM_INSTRUCTION_VERSION,
    PLATFORM_SYSTEM_INSTRUCTION,
)
from apps.conversations.models import (
    ChatTurn,
    Conversation,
    GenerationSubmission,
    Message,
)
from apps.conversations.services.acceptance import accept_generation
from apps.conversations.services.contracts import (
    AcceptedGeneration,
    ReplayedGeneration,
)
from apps.conversations.services.exceptions import (
    ChatTurnAlreadyInProgress,
    IdempotencyKeyReused,
)
from apps.conversations.services.orchestration import (
    MAX_CONTEXT_PREPARATION_ATTEMPTS,
    prepare_and_accept_generation,
)


User = get_user_model()


class PrepareAndAcceptGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="orchestration@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Orchestration tests",
        )

        self.generation_config = GeminiConfig(
            api_key="test-secret-api-key",
            model="gemini-test-model",
            thinking_level="LOW",
            max_output_tokens=4096,
            timeout_ms=30000,
        )

        config_patcher = patch(
            "apps.conversations.services.orchestration.get_gemini_config",
            return_value=self.generation_config,
        )
        self.get_gemini_config = config_patcher.start()
        self.addCleanup(config_patcher.stop)

    def build_message(self, content="Explain orchestration."):
        return Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content=content,
        )

    def build_context(self, message):
        return PreparedConversationContext(
            current_message_id=message.id,
            messages=(
                ConversationMessage(
                    role="user",
                    content=message.content,
                ),
            ),
            system_instruction=PLATFORM_SYSTEM_INSTRUCTION,
            platform_instruction_version=PLATFORM_INSTRUCTION_VERSION,
            platform_instruction_snapshot=PLATFORM_SYSTEM_INSTRUCTION,
            custom_instruction_snapshot=None,
            eligible_history_message_ids=(),
            selected_history_message_ids=(),
            input_tokens=20,
            max_input_tokens=32768,
        )

    def build_request(self, content="Explain orchestration.", key=None):
        message = self.build_message(content)
        return {
            "user": self.user,
            "conversation_id": self.conversation.id,
            "current_user_message": message,
            "idempotency_key": key or uuid.uuid4(),
            "request_hash": hash_message_content(content),
        }

    def seed_accepted_generation(self, request):
        return accept_generation(
            **request,
            prepared_context=self.build_context(
                request["current_user_message"]
            ),
            generation_config=self.generation_config,
        )

    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay",
        return_value=None,
    )
    def test_new_request_persists_configuration_through_real_acceptance(
        self,
        find_replay,
        prepare_context,
    ):
        request = self.build_request()
        prepared = self.build_context(request["current_user_message"])
        prepare_context.return_value = prepared

        result = prepare_and_accept_generation(**request)

        self.assertIsInstance(result, AcceptedGeneration)
        find_replay.assert_called_once()
        self.get_gemini_config.assert_called_once_with()
        prepare_context.assert_called_once_with(
            conversation=self.conversation,
            current_user_message=request["current_user_message"],
            generation_config=self.generation_config,
        )

        turn = ChatTurn.objects.get(
            idempotency_key=request["idempotency_key"],
        )
        self.assertEqual(
            turn.generation_metadata,
            {
                "schema_version": 1,
                "provider": "gemini",
                "requested_model": "gemini-test-model",
                "thinking_level": "LOW",
            },
        )
        self.assertEqual(turn.max_output_tokens, 4096)
        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)

    @patch(
        "apps.conversations.services.orchestration.accept_generation"
    )
    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay"
    )
    def test_new_request_is_prepared_and_accepted(
        self,
        find_replay,
        prepare_context,
        accept,
    ):
        request = self.build_request()
        prepared = self.build_context(request["current_user_message"])
        result = AcceptedGeneration(chat_turn=None)

        find_replay.return_value = None
        prepare_context.return_value = prepared
        accept.return_value = result

        actual = prepare_and_accept_generation(**request)

        self.assertIs(actual, result)
        find_replay.assert_called_once()
        self.get_gemini_config.assert_called_once_with()

        prepare_context.assert_called_once_with(
            conversation=self.conversation,
            current_user_message=request["current_user_message"],
            generation_config=self.generation_config,
        )
        accept.assert_called_once_with(
            **request,
            prepared_context=prepared,
            generation_config=self.generation_config,
        )

    @patch(
        "apps.conversations.services.orchestration.accept_generation"
    )
    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay"
    )
    def test_existing_replay_returns_before_context_preparation(
        self,
        find_replay,
        prepare_context,
        accept,
    ):
        request = self.build_request()
        replay = ReplayedGeneration(chat_turn=None)
        find_replay.return_value = replay

        actual = prepare_and_accept_generation(**request)

        self.assertIs(actual, replay)
        find_replay.assert_called_once()
        self.get_gemini_config.assert_not_called()
        prepare_context.assert_not_called()
        accept.assert_not_called()

    @patch(
        "apps.conversations.services.orchestration.accept_generation"
    )
    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay"
    )
    def test_stale_snapshot_retries_with_reloaded_conversation(
        self,
        find_replay,
        prepare_context,
        accept,
    ):
        request = self.build_request()
        find_replay.return_value = None

        prepared = self.build_context(request["current_user_message"])
        prepare_context.return_value = prepared

        accepted = AcceptedGeneration(chat_turn=None)

        def accept_side_effect(**kwargs):
            if accept.call_count == 1:
                Conversation.objects.filter(
                    pk=self.conversation.pk
                ).update(custom_instructions="Updated instructions")
                raise ContextSnapshotStale()

            return accepted

        accept.side_effect = accept_side_effect

        actual = prepare_and_accept_generation(**request)

        self.assertIs(actual, accepted)
        self.assertEqual(prepare_context.call_count, 2)
        self.assertEqual(accept.call_count, 2)
        self.get_gemini_config.assert_called_once_with()

        for call in prepare_context.call_args_list:
            self.assertIs(
                call.kwargs["generation_config"],
                self.generation_config,
            )

        for call in accept.call_args_list:
            self.assertIs(
                call.kwargs["generation_config"],
                self.generation_config,
            )

        prepared_conversations = [
            call.kwargs["conversation"]
            for call in prepare_context.call_args_list
        ]

        self.assertIsNone(
            prepared_conversations[0].custom_instructions
        )
        self.assertEqual(
            prepared_conversations[1].custom_instructions,
            "Updated instructions",
        )

        self.assertTrue(request["current_user_message"]._state.adding)

    @patch(
        "apps.conversations.services.orchestration.accept_generation"
    )
    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay"
    )
    def test_three_stale_snapshots_raise_context_changed(
        self,
        find_replay,
        prepare_context,
        accept,
    ):
        request = self.build_request()
        find_replay.return_value = None
        prepare_context.return_value = self.build_context(
            request["current_user_message"]
        )
        accept.side_effect = ContextSnapshotStale()

        with self.assertRaises(ContextChanged) as context:
            prepare_and_accept_generation(**request)

        self.assertEqual(
            prepare_context.call_count,
            MAX_CONTEXT_PREPARATION_ATTEMPTS,
        )
        self.assertEqual(
            accept.call_count,
            MAX_CONTEXT_PREPARATION_ATTEMPTS,
        )
        self.get_gemini_config.assert_called_once_with()

        for call in prepare_context.call_args_list:
            self.assertIs(
                call.kwargs["generation_config"],
                self.generation_config,
            )

        for call in accept.call_args_list:
            self.assertIs(
                call.kwargs["generation_config"],
                self.generation_config,
            )

        self.assertIsInstance(
            context.exception.__cause__,
            ContextSnapshotStale,
        )
        self.assertTrue(request["current_user_message"]._state.adding)

    @patch(
        "apps.conversations.services.orchestration.accept_generation"
    )
    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay"
    )
    def test_context_preflight_failure_propagates_without_acceptance(
        self,
        find_replay,
        prepare_context,
        accept,
    ):
        request = self.build_request()
        find_replay.return_value = None
        prepare_context.side_effect = ContextUnavailable()

        with self.assertRaises(ContextUnavailable):
            prepare_and_accept_generation(**request)

        prepare_context.assert_called_once()
        accept.assert_not_called()

    def test_context_unavailable_returns_replay_found_on_second_lookup(self):
        request = self.build_request()
        replay = ReplayedGeneration(chat_turn=None)

        with (
            patch(
                "apps.conversations.services.orchestration.find_idempotent_replay",
                side_effect=[None, replay],
            ) as find_replay,
            patch(
                "apps.conversations.services.orchestration.prepare_conversation_context",
                side_effect=ContextUnavailable(),
            ) as prepare_context,
            patch(
                "apps.conversations.services.orchestration.accept_generation"
            ) as accept,
        ):
            result = prepare_and_accept_generation(**request)

        self.assertIs(result, replay)
        self.assertEqual(find_replay.call_count, 2)
        prepare_context.assert_called_once()
        accept.assert_not_called()

    def test_context_unavailable_propagates_when_second_lookup_finds_nothing(self):
        request = self.build_request()

        with (
            patch(
                "apps.conversations.services.orchestration.find_idempotent_replay",
                return_value=None,
            ) as find_replay,
            patch(
                "apps.conversations.services.orchestration.prepare_conversation_context",
                side_effect=ContextUnavailable(),
            ) as prepare_context,
            patch(
                "apps.conversations.services.orchestration.accept_generation"
            ) as accept,
        ):
            with self.assertRaises(ContextUnavailable):
                prepare_and_accept_generation(**request)

        self.assertEqual(find_replay.call_count, 2)
        prepare_context.assert_called_once()
        accept.assert_not_called()

    def test_context_limit_exceeded_returns_replay_found_on_second_lookup(self):
        request = self.build_request()
        replay = ReplayedGeneration(chat_turn=None)

        with (
            patch(
                "apps.conversations.services.orchestration.find_idempotent_replay",
                side_effect=[None, replay],
            ) as find_replay,
            patch(
                "apps.conversations.services.orchestration.prepare_conversation_context",
                side_effect=ContextLimitExceeded(),
            ) as prepare_context,
            patch(
                "apps.conversations.services.orchestration.accept_generation"
            ) as accept,
        ):
            result = prepare_and_accept_generation(**request)

        self.assertIs(result, replay)
        self.assertEqual(find_replay.call_count, 2)
        prepare_context.assert_called_once()
        accept.assert_not_called()

    def test_context_limit_exceeded_propagates_when_second_lookup_finds_nothing(self):
        request = self.build_request()

        with (
            patch(
                "apps.conversations.services.orchestration.find_idempotent_replay",
                return_value=None,
            ) as find_replay,
            patch(
                "apps.conversations.services.orchestration.prepare_conversation_context",
                side_effect=ContextLimitExceeded(),
            ) as prepare_context,
            patch(
                "apps.conversations.services.orchestration.accept_generation"
            ) as accept,
        ):
            with self.assertRaises(ContextLimitExceeded):
                prepare_and_accept_generation(**request)

        self.assertEqual(find_replay.call_count, 2)
        prepare_context.assert_called_once()
        accept.assert_not_called()

    @patch(
        "apps.conversations.services.orchestration.accept_generation"
    )
    @patch(
        "apps.conversations.services.orchestration.prepare_conversation_context"
    )
    @patch(
        "apps.conversations.services.orchestration.find_idempotent_replay"
    )
    def test_acceptance_error_propagates_without_retry(
        self,
        find_replay,
        prepare_context,
        accept,
    ):
        request = self.build_request()
        find_replay.return_value = None
        prepare_context.return_value = self.build_context(
            request["current_user_message"]
        )
        accept.side_effect = ChatTurnAlreadyInProgress()

        with self.assertRaises(ChatTurnAlreadyInProgress):
            prepare_and_accept_generation(**request)

        prepare_context.assert_called_once()
        accept.assert_called_once()

    def test_existing_replay_does_not_consume_additional_quota(self):
        original_request = self.build_request()
        original_result = self.seed_accepted_generation(original_request)

        replay_request = self.build_request(
            content="Explain orchestration.",
            key=original_request["idempotency_key"],
        )

        with (
            patch(
                "apps.conversations.services.orchestration.prepare_conversation_context"
            ) as prepare_context,
            patch(
                "apps.conversations.services.orchestration.accept_generation"
            ) as accept,
        ):
            result = prepare_and_accept_generation(**replay_request)

        self.assertIsInstance(result, ReplayedGeneration)
        self.assertEqual(
            result.chat_turn.id,
            original_result.chat_turn.id,
        )
        prepare_context.assert_not_called()
        accept.assert_not_called()
        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(ChatTurn.objects.count(), 1)

    def test_existing_key_with_different_content_fails_before_preparation(self):
        original_request = self.build_request("Original content.")
        self.seed_accepted_generation(original_request)

        changed_request = self.build_request(
            content="Different content.",
            key=original_request["idempotency_key"],
        )

        with patch(
            "apps.conversations.services.orchestration.prepare_conversation_context"
        ) as prepare_context:
            with self.assertRaises(IdempotencyKeyReused):
                prepare_and_accept_generation(**changed_request)

        prepare_context.assert_not_called()
        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(ChatTurn.objects.count(), 1)
