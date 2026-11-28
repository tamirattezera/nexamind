import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, close_old_connections, connection
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from apps.ai.config import GeminiConfig
from apps.ai.contracts import (
    ConversationMessage,
    GenerationRequest,
    GenerationResult,
)
from apps.conversations.services.execution import GenerationExecutionInput
from apps.ai.providers.gemini import (
    ProviderBlockedError,
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from apps.conversations.models import ChatTurn, Conversation, Message
from apps.conversations.services.contracts import (
    AcceptedGeneration,
    ReplayedGeneration,
)

User = get_user_model()


class ExecuteGenerationTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="execution-service@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Execution service tests",
        )

        self.user_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Explain Django transactions.",
        )

        self.chat_turn = ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=self.user_message,
            idempotency_key=uuid.uuid4(),
            request_hash="a" * 64,
            status=ChatTurn.Status.IN_PROGRESS,
            generation_metadata={
                "schema_version": 1,
                "provider": "gemini",
                "requested_model": "gemini-test-model",
                "thinking_level": "LOW",
            },
            max_output_tokens=4096,
            system_instruction_version="platform-v1",
            system_instruction_snapshot="You are NexaMind.",
            selected_history_message_ids=[],
        )

        self.accepted = AcceptedGeneration(chat_turn=self.chat_turn)

        self.execution_input = GenerationExecutionInput(
            request=GenerationRequest(
                messages=(
                    ConversationMessage(
                        role="user",
                        content="Explain Django transactions.",
                    ),
                ),
                system_instruction="You are NexaMind.",
            ),
            config=GeminiConfig(
                api_key="test-api-key",
                model="gemini-test-model",
                thinking_level="LOW",
                max_output_tokens=4096,
                timeout_ms=30000,
            ),
        )

        self.generation_result = GenerationResult(
            text="Django transactions provide atomic database operations.",
            model_name="gemini-test-model",
            input_tokens=20,
            output_tokens=12,
            total_tokens=32,
            thinking_tokens=3,
            finish_reason="STOP",
            response_id="response-test-123",
        )

    @patch("apps.conversations.services.execution_service.generate_response")
    @patch("apps.conversations.services.execution_service.prepare_generation_execution")
    def test_successfully_persists_assistant_response(
        self,
        prepare_execution,
        generate_response,
    ):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        prepare_execution.return_value = self.execution_input
        generate_response.return_value = self.generation_result

        result = execute_generation(self.accepted)

        self.chat_turn.refresh_from_db()

        self.assertEqual(result.pk, self.chat_turn.pk)
        self.assertEqual(
            self.chat_turn.status,
            ChatTurn.Status.COMPLETED,
        )
        self.assertIsNotNone(self.chat_turn.completed_at)
        self.assertEqual(
            self.chat_turn.assistant_message.role,
            Message.Role.ASSISTANT,
        )
        self.assertEqual(
            self.chat_turn.assistant_message.content,
            self.generation_result.text,
        )
        self.assertEqual(
            self.chat_turn.model_name,
            self.generation_result.model_name,
        )
        self.assertEqual(self.chat_turn.input_tokens, 20)
        self.assertEqual(self.chat_turn.output_tokens, 12)
        self.assertEqual(self.chat_turn.total_tokens, 32)
        self.assertIsNone(self.chat_turn.error_code)
        self.assertIsNone(self.chat_turn.error_message)

        prepare_execution.assert_called_once_with(self.chat_turn)
        generate_response.assert_called_once_with(
            self.execution_input.request,
            config=self.execution_input.config,
        )

        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation,
                role=Message.Role.ASSISTANT,
            ).count(),
            1,
        )

    def assert_generation_failed(
        self,
        exception,
        expected_error_code,
        expected_message,
        *,
        preparation_error=False,
    ):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        prepare_path = (
            "apps.conversations.services.execution_service.prepare_generation_execution"
        )
        generate_path = (
            "apps.conversations.services.execution_service.generate_response"
        )

        with patch(prepare_path) as prepare_execution:
            with patch(generate_path) as generate_response:
                if preparation_error:
                    prepare_execution.side_effect = exception
                else:
                    prepare_execution.return_value = self.execution_input
                    generate_response.side_effect = exception

                execute_generation(self.accepted)

        self.chat_turn.refresh_from_db()

        self.assertEqual(
            self.chat_turn.status,
            ChatTurn.Status.FAILED,
        )
        self.assertIsNotNone(self.chat_turn.completed_at)
        self.assertEqual(
            self.chat_turn.error_code,
            expected_error_code,
        )
        self.assertEqual(
            self.chat_turn.error_message,
            expected_message,
        )
        self.assertIsNone(self.chat_turn.assistant_message_id)

        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation,
                role=Message.Role.ASSISTANT,
            ).count(),
            0,
        )

    def test_provider_timeout_marks_turn_failed(self):
        self.assert_generation_failed(
            ProviderTimeoutError("secret provider details"),
            "AI_PROVIDER_TIMEOUT",
            "The AI provider request timed out.",
        )

    def test_other_provider_error_marks_turn_failed(self):
        self.assert_generation_failed(
            ProviderError("secret provider details"),
            "AI_PROVIDER_ERROR",
            "The AI provider could not complete the request.",
        )

    def test_provider_unavailable_error_marks_turn_failed(self):
        self.assert_generation_failed(
            ProviderUnavailableError("secret provider details"),
            "AI_PROVIDER_ERROR",
            "The AI provider could not complete the request.",
        )

    def test_provider_response_error_marks_turn_failed(self):
        self.assert_generation_failed(
            ProviderResponseError("secret provider details"),
            "AI_PROVIDER_ERROR",
            "The AI provider could not complete the request.",
        )

    def test_provider_blocked_error_marks_turn_failed(self):
        self.assert_generation_failed(
            ProviderBlockedError("secret provider details"),
            "AI_PROVIDER_ERROR",
            "The AI provider could not complete the request.",
        )

    def test_invalid_persisted_configuration_marks_turn_failed(self):
        self.assert_generation_failed(
            ImproperlyConfigured("secret configuration details"),
            "INTERNAL_SERVER_ERROR",
            "An internal error prevented generation from completing.",
            preparation_error=True,
        )

    def test_unexpected_execution_exception_marks_turn_failed(self):
        self.assert_generation_failed(
            RuntimeError("secret internal details"),
            "INTERNAL_SERVER_ERROR",
            "An internal error prevented generation from completing.",
        )

    def test_replayed_generation_is_rejected(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        replay = ReplayedGeneration(chat_turn=self.chat_turn)

        with patch(
            "apps.conversations.services.execution_service.generate_response"
        ) as generate_response:
            with self.assertRaises(TypeError):
                execute_generation(replay)

        generate_response.assert_not_called()

    def test_completed_turn_is_rejected_without_provider_call(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        self.chat_turn.status = ChatTurn.Status.COMPLETED
        self.chat_turn.assistant_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="Already completed.",
        )
        self.chat_turn.completed_at = timezone.now()
        self.chat_turn.save()

        with patch(
            "apps.conversations.services.execution_service.generate_response"
        ) as generate_response:
            with self.assertRaises(ValueError):
                execute_generation(self.accepted)

        generate_response.assert_not_called()


    @patch(
        "apps.conversations.services.execution_service.generate_response"
    )
    @patch(
        "apps.conversations.services.execution_service.prepare_generation_execution"
    )
    def test_provider_call_runs_outside_database_transaction(
        self,
        prepare_execution,
        generate_response,
    ):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        prepare_execution.return_value = self.execution_input
        generate_response.return_value = self.generation_result

        initial_atomic_depth = len(connection.atomic_blocks)

        def assert_outside_transaction(*args, **kwargs):
            self.assertEqual(
                len(connection.atomic_blocks),
                initial_atomic_depth,
                "The provider call must not open an additional database transaction.",
            )
            return self.generation_result

        generate_response.side_effect = assert_outside_transaction

        execute_generation(self.accepted)

        generate_response.assert_called_once()

    @skipUnlessDBFeature("has_select_for_update")
    def test_competing_worker_does_not_call_provider_twice(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        provider_started = Event()
        release_provider = Event()
        provider_calls = []

        def first_worker():
            close_old_connections()
            try:
                with patch(
                    "apps.conversations.services.execution_service.prepare_generation_execution",
                    return_value=self.execution_input,
                ):
                    def blocking_provider(*args, **kwargs):
                        provider_calls.append("called")
                        provider_started.set()
                        if not release_provider.wait(timeout=10):
                            raise TimeoutError("Provider release timed out.")
                        return self.generation_result

                    with patch(
                        "apps.conversations.services.execution_service.generate_response",
                        side_effect=blocking_provider,
                    ):
                        return execute_generation(self.accepted)
            finally:
                close_old_connections()

        def second_worker():
            close_old_connections()
            try:
                return execute_generation(self.accepted)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(first_worker)
            try:
                self.assertTrue(provider_started.wait(timeout=5))

                second = executor.submit(second_worker)
                second_result = second.result(timeout=5)

                self.assertEqual(
                    second_result.status,
                    ChatTurn.Status.IN_PROGRESS,
                )
                self.assertEqual(provider_calls, ["called"])
            finally:
                release_provider.set()

            first_result = first.result(timeout=10)

        self.chat_turn.refresh_from_db()
        self.assertEqual(first_result.status, ChatTurn.Status.COMPLETED)
        self.assertEqual(self.chat_turn.status, ChatTurn.Status.COMPLETED)
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)
        self.assertEqual(provider_calls, ["called"])

    def test_execution_claim_is_persisted_before_provider_call(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        observed_claims = []

        with patch(
            "apps.conversations.services.execution_service.prepare_generation_execution",
            return_value=self.execution_input,
        ):
            def inspect_claim(*args, **kwargs):
                turn = ChatTurn.objects.get(pk=self.chat_turn.pk)
                observed_claims.append(
                    (turn.execution_claim_id, turn.execution_claimed_at)
                )
                return self.generation_result

            with patch(
                "apps.conversations.services.execution_service.generate_response",
                side_effect=inspect_claim,
            ) as generate_response:
                result = execute_generation(self.accepted)

        self.assertEqual(len(observed_claims), 1)
        self.assertIsNotNone(observed_claims[0][0])
        self.assertIsNotNone(observed_claims[0][1])

        self.chat_turn.refresh_from_db()
        self.assertEqual(result.status, ChatTurn.Status.COMPLETED)
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)
        generate_response.assert_called_once()

    def test_late_provider_failure_is_rejected_after_claim_is_cleared(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        observed_claims = []

        def simulate_recovery_then_provider_failure(*args, **kwargs):
            turn = ChatTurn.objects.get(pk=self.chat_turn.pk)
            observed_claims.append(turn.execution_claim_id)

            ChatTurn.objects.filter(pk=turn.pk).update(
                status=ChatTurn.Status.FAILED,
                error_code="CHAT_TURN_PROCESSING_TIMEOUT",
                error_message="Generation processing timed out.",
                completed_at=timezone.now(),
                execution_claim_id=None,
                execution_claimed_at=None,
            )

            raise ProviderError("Late provider failure.")

        with patch(
            "apps.conversations.services.execution_service.prepare_generation_execution",
            return_value=self.execution_input,
        ):
            with patch(
                "apps.conversations.services.execution_service.generate_response",
                side_effect=simulate_recovery_then_provider_failure,
            ) as generate_response:
                result = execute_generation(self.accepted)

        self.assertEqual(len(observed_claims), 1)
        self.assertIsNotNone(observed_claims[0])
        generate_response.assert_called_once()

        self.chat_turn.refresh_from_db()
        self.assertEqual(result.status, ChatTurn.Status.FAILED)
        self.assertEqual(
            self.chat_turn.error_code,
            "CHAT_TURN_PROCESSING_TIMEOUT",
        )
        self.assertIsNone(self.chat_turn.assistant_message_id)
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)

    def test_late_provider_success_is_rejected_after_claim_is_cleared(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        observed_claims = []

        def simulate_recovery(*args, **kwargs):
            turn = ChatTurn.objects.get(pk=self.chat_turn.pk)
            observed_claims.append(turn.execution_claim_id)

            # Simulate the recovery worker winning while Gemini is running.
            ChatTurn.objects.filter(pk=turn.pk).update(
                status=ChatTurn.Status.FAILED,
                error_code="CHAT_TURN_PROCESSING_TIMEOUT",
                error_message="Generation processing timed out.",
                completed_at=timezone.now(),
                execution_claim_id=None,
                execution_claimed_at=None,
            )

            # Gemini returns successfully, but its worker has lost ownership.
            return self.generation_result

        with patch(
            "apps.conversations.services.execution_service.prepare_generation_execution",
            return_value=self.execution_input,
        ):
            with patch(
                "apps.conversations.services.execution_service.generate_response",
                side_effect=simulate_recovery,
            ) as generate_response:
                result = execute_generation(self.accepted)

        self.assertEqual(len(observed_claims), 1)
        self.assertIsNotNone(observed_claims[0])
        generate_response.assert_called_once()

        self.chat_turn.refresh_from_db()
        self.assertEqual(result.status, ChatTurn.Status.FAILED)
        self.assertEqual(
            self.chat_turn.error_code,
            "CHAT_TURN_PROCESSING_TIMEOUT",
        )
        self.assertIsNone(self.chat_turn.assistant_message_id)
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)
        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation,
                role=Message.Role.ASSISTANT,
            ).count(),
            0,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_recovery_wins_against_late_provider_success(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )
        from apps.conversations.services.stale_recovery import (
            recover_stale_turns,
        )

        provider_started = Event()
        release_provider = Event()

        def execution_worker():
            close_old_connections()
            try:
                with patch(
                    "apps.conversations.services.execution_service.prepare_generation_execution",
                    return_value=self.execution_input,
                ):
                    def blocking_provider(*args, **kwargs):
                        provider_started.set()
                        if not release_provider.wait(timeout=10):
                            raise TimeoutError("Provider release timed out.")
                        return self.generation_result

                    with patch(
                        "apps.conversations.services.execution_service.generate_response",
                        side_effect=blocking_provider,
                    ):
                        return execute_generation(self.accepted)
            finally:
                close_old_connections()

        def recovery_worker():
            close_old_connections()
            try:
                return recover_stale_turns()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            execution = executor.submit(execution_worker)

            try:
                self.assertTrue(
                    provider_started.wait(timeout=5),
                    "The provider worker did not start.",
                )

                ChatTurn.objects.filter(pk=self.chat_turn.pk).update(
                    execution_claimed_at=(
                        timezone.now() - timedelta(minutes=5)
                    ),
                )

                recovery = executor.submit(recovery_worker)
                recovered_count = recovery.result(timeout=5)

                self.assertEqual(recovered_count, 1)
            finally:
                release_provider.set()

            execution_result = execution.result(timeout=10)

        self.chat_turn.refresh_from_db()

        self.assertEqual(
            execution_result.status,
            ChatTurn.Status.FAILED,
        )
        self.assertEqual(
            self.chat_turn.status,
            ChatTurn.Status.FAILED,
        )
        self.assertEqual(
            self.chat_turn.error_code,
            "CHAT_TURN_PROCESSING_TIMEOUT",
        )
        self.assertIsNotNone(self.chat_turn.completed_at)
        self.assertIsNone(self.chat_turn.assistant_message_id)
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)

        self.assertEqual(
            Message.objects.filter(
                conversation=self.conversation,
                role=Message.Role.ASSISTANT,
            ).count(),
            0,
        )
        self.assertTrue(
            Message.objects.filter(
                pk=self.user_message.pk,
                role=Message.Role.USER,
            ).exists()
        )

    def test_deleted_conversation_discards_late_provider_success(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        def delete_conversation_during_provider_call(*args, **kwargs):
            Conversation.objects.filter(pk=self.conversation.pk).delete()
            return self.generation_result

        with patch(
            "apps.conversations.services.execution_service.prepare_generation_execution",
            return_value=self.execution_input,
        ):
            with patch(
                "apps.conversations.services.execution_service.generate_response",
                side_effect=delete_conversation_during_provider_call,
            ) as generate_response:
                with self.assertRaises(Conversation.DoesNotExist):
                    execute_generation(self.accepted)

        generate_response.assert_called_once()
        self.assertFalse(
            Conversation.objects.filter(pk=self.conversation.pk).exists()
        )
        self.assertFalse(
            ChatTurn.objects.filter(pk=self.chat_turn.pk).exists()
        )
        self.assertEqual(
            Message.objects.filter(conversation_id=self.conversation.pk).count(),
            0,
        )

    def test_deleted_conversation_discards_late_provider_failure(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        def delete_conversation_then_fail(*args, **kwargs):
            Conversation.objects.filter(pk=self.conversation.pk).delete()
            raise ProviderError("Provider failed after conversation deletion.")

        with patch(
            "apps.conversations.services.execution_service.prepare_generation_execution",
            return_value=self.execution_input,
        ):
            with patch(
                "apps.conversations.services.execution_service.generate_response",
                side_effect=delete_conversation_then_fail,
            ) as generate_response:
                with self.assertRaises(Conversation.DoesNotExist):
                    execute_generation(self.accepted)

        generate_response.assert_called_once()
        self.assertFalse(
            Conversation.objects.filter(pk=self.conversation.pk).exists()
        )
        self.assertFalse(
            ChatTurn.objects.filter(pk=self.chat_turn.pk).exists()
        )
        self.assertEqual(
            Message.objects.filter(conversation_id=self.conversation.pk).count(),
            0,
        )

    def test_success_persistence_error_is_not_recorded_as_provider_failure(self):
        from apps.conversations.services.execution_service import (
            execute_generation,
        )

        with patch(
            "apps.conversations.services.execution_service.prepare_generation_execution",
            return_value=self.execution_input,
        ):
            with patch(
                "apps.conversations.services.execution_service.generate_response",
                return_value=self.generation_result,
            ):
                with patch(
                    "apps.conversations.services.execution_service.Message.objects.create",
                    side_effect=IntegrityError("database failure"),
                ):
                    with self.assertRaises(IntegrityError):
                        execute_generation(self.accepted)

        self.chat_turn.refresh_from_db()

        self.assertEqual(
            self.chat_turn.status,
            ChatTurn.Status.IN_PROGRESS,
        )
        self.assertIsNone(self.chat_turn.assistant_message_id)
        self.assertIsNone(self.chat_turn.error_code)
        self.assertIsNone(self.chat_turn.completed_at)
