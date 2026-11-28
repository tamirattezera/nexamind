import uuid
from dataclasses import replace

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ai.config import GeminiConfig
from apps.ai.contracts import ConversationMessage
from apps.conversations.context.contracts import PreparedConversationContext
from apps.conversations.context.exceptions import ContextSnapshotStale
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

from .acceptance import accept_generation
from .contracts import AcceptedGeneration, ReplayedGeneration
from .exceptions import (
    ChatTurnAlreadyInProgress,
    GenerationRateLimitExceeded,
    IdempotencyKeyReused,
)

User = get_user_model()


class AcceptGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="acceptance@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Acceptance tests",
        )

    def build_request(self, content, conversation=None, key=None):
        conversation = conversation or self.conversation
        key = key or uuid.uuid4()

        message = Message(
            conversation=conversation,
            role=Message.Role.USER,
            content=content,
        )

        request_hash = hash_message_content(content)

        prepared_context = PreparedConversationContext(
            current_message_id=message.id,
            messages=(
                ConversationMessage(
                    role="user",
                    content=content,
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

        return {
            "user": self.user,
            "conversation_id": conversation.id,
            "current_user_message": message,
            "idempotency_key": key,
            "request_hash": request_hash,
            "prepared_context": prepared_context,
            "generation_config": GeminiConfig(
                api_key="test-secret-api-key",
                model="gemini-test-model",
                thinking_level="LOW",
                max_output_tokens=4096,
                timeout_ms=30000,
            ),
        }

    def accept(self, **request):
        return accept_generation(**request)

    def test_successfully_accepts_generation_atomically(self):
        request = self.build_request("Explain database transactions.")

        result = self.accept(**request)

        self.assertIsInstance(result, AcceptedGeneration)

        turn = result.chat_turn
        request["current_user_message"].refresh_from_db()

        self.assertEqual(turn.status, ChatTurn.Status.IN_PROGRESS)
        self.assertEqual(turn.conversation, self.conversation)
        self.assertEqual(
            turn.user_message.content,
            "Explain database transactions.",
        )
        self.assertEqual(turn.request_hash, request["request_hash"])
        self.assertEqual(
            turn.system_instruction_version,
            PLATFORM_INSTRUCTION_VERSION,
        )

        self.assertEqual(
            GenerationSubmission.objects.filter(user=self.user).count(),
            1,
        )
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation,
                role=Message.Role.USER,
            ).count(),
            1,
        )
        self.assertEqual(
            ChatTurn.objects.filter(conversation=self.conversation).count(),
            1,
        )

    def test_mid_write_database_failure_rolls_back_all_acceptance_records(self):
        from unittest.mock import patch
        from django.db import IntegrityError

        request = self.build_request("Test atomic acceptance rollback.")

        with patch(
            "apps.conversations.services.acceptance.ChatTurn.objects.create",
            side_effect=IntegrityError("simulated ChatTurn insert failure"),
        ):
            with self.assertRaises(IntegrityError):
                self.accept(**request)

        self.assertEqual(
            GenerationSubmission.objects.filter(user=self.user).count(),
            0,
        )
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation,
                role=Message.Role.USER,
            ).count(),
            0,
        )
        self.assertEqual(
            ChatTurn.objects.filter(conversation=self.conversation).count(),
            0,
        )

    def test_generation_configuration_is_persisted_without_secrets(self):
        request = self.build_request("Explain generation configuration.")
        config = GeminiConfig(
            api_key="test-secret-api-key",
            model="gemini-test-model",
            thinking_level="HIGH",
            max_output_tokens=4096,
            timeout_ms=30000,
        )

        request["generation_config"] = config
        result = self.accept(**request)

        turn = result.chat_turn
        turn.refresh_from_db()

        self.assertEqual(
            turn.generation_metadata,
            {
                "schema_version": 1,
                "provider": "gemini",
                "requested_model": "gemini-test-model",
                "thinking_level": "HIGH",
            },
        )
        self.assertEqual(turn.max_output_tokens, 4096)

        self.assertNotIn("api_key", turn.generation_metadata)
        self.assertNotIn("timeout_ms", turn.generation_metadata)
        self.assertNotIn("test-secret-api-key", str(turn.generation_metadata))

    def test_matching_active_request_returns_existing_turn(self):
        first_request = self.build_request(
            "Explain idempotency.",
        )
        first_result = self.accept(**first_request)

        replay_request = self.build_request(
            "Explain idempotency.",
            key=first_request["idempotency_key"],
        )
        replay_result = self.accept(**replay_request)

        self.assertIsInstance(replay_result, ReplayedGeneration)
        self.assertEqual(
            replay_result.chat_turn.id,
            first_result.chat_turn.id,
        )

        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(ChatTurn.objects.count(), 1)

    def test_reused_key_with_different_content_is_rejected(self):
        first_request = self.build_request("Original content.")
        self.accept(**first_request)

        changed_request = self.build_request(
            "Different content.",
            key=first_request["idempotency_key"],
        )

        with self.assertRaises(IdempotencyKeyReused):
            self.accept(**changed_request)

        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(ChatTurn.objects.count(), 1)

    def test_different_request_is_rejected_while_turn_is_active(self):
        first_request = self.build_request("First request.")
        self.accept(**first_request)

        second_request = self.build_request("Second request.")

        with self.assertRaises(ChatTurnAlreadyInProgress):
            self.accept(**second_request)

        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(ChatTurn.objects.count(), 1)

    def test_stale_context_creates_no_database_records(self):
        request = self.build_request("Check context freshness.")

        request["prepared_context"] = replace(
            request["prepared_context"],
            custom_instruction_snapshot="Outdated instruction",
        )

        with self.assertRaises(ContextSnapshotStale):
            self.accept(**request)

        self.assertEqual(GenerationSubmission.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(ChatTurn.objects.count(), 0)
        self.assertTrue(request["current_user_message"]._state.adding)

    def test_rate_limit_rejection_creates_no_additional_records(self):
        with override_settings(
            CHAT_GENERATION_RATE_LIMIT=1,
            CHAT_GENERATION_RATE_WINDOW_SECONDS=60,
        ):
            first_request = self.build_request("First conversation request.")
            self.accept(**first_request)

            another_conversation = Conversation.objects.create(
                user=self.user,
                title="Second conversation",
            )

            second_request = self.build_request(
                "Second conversation request.",
                conversation=another_conversation,
            )

            with self.assertRaises(GenerationRateLimitExceeded):
                self.accept(**second_request)

        self.assertEqual(GenerationSubmission.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(ChatTurn.objects.count(), 1)
        self.assertTrue(second_request["current_user_message"]._state.adding)

    def test_user_cannot_accept_generation_in_another_users_conversation(self):
        other_user = User.objects.create_user(
            email="other-acceptance@example.com",
            password="StrongTestPassword123!",
        )

        other_conversation = Conversation.objects.create(
            user=other_user,
            title="Private conversation",
        )

        request = self.build_request(
            "Unauthorized request.",
            conversation=other_conversation,
        )

        with self.assertRaises(Conversation.DoesNotExist):
            self.accept(**request)

        self.assertEqual(GenerationSubmission.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(ChatTurn.objects.count(), 0)
