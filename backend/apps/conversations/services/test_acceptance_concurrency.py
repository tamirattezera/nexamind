import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.ai.config import GeminiConfig
from apps.ai.contracts import ConversationMessage
from apps.conversations.context.contracts import PreparedConversationContext
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
from .exceptions import ChatTurnAlreadyInProgress
from concurrent.futures import TimeoutError
from threading import Event

User = get_user_model()


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentGenerationAcceptanceTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            email="concurrent-acceptance@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Concurrent acceptance",
        )

    def build_request(self, content):
        message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content=content,
        )

        prepared_context = PreparedConversationContext(
            current_message_id=message.id,
            messages=(ConversationMessage(role="user", content=content),),
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
            "conversation_id": self.conversation.id,
            "current_user_message": message,
            "idempotency_key": uuid.uuid4(),
            "request_hash": hash_message_content(content),
            "prepared_context": prepared_context,
            "generation_config": GeminiConfig(
                api_key="test-secret-api-key",
                model="gemini-test-model",
                thinking_level="LOW",
                max_output_tokens=4096,
                timeout_ms=30000,
            ),
        }

    def run_acceptance(self, barrier, request):
        close_old_connections()
        try:
            barrier.wait(timeout=10)

            try:
                result = accept_generation(**request)
                return ("accepted", result.chat_turn.id)
            except ChatTurnAlreadyInProgress:
                return ("rejected", None)
        finally:
            close_old_connections()

    def test_concurrent_different_requests_accept_only_one_turn(self):
        requests = [
            self.build_request("First concurrent request."),
            self.build_request("Second concurrent request."),
        ]
        barrier = Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self.run_acceptance, barrier, request)
                for request in requests
            ]
            outcomes = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(
            [outcome[0] for outcome in outcomes],
            ["accepted", "rejected"],
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
            ChatTurn.objects.filter(
                conversation=self.conversation,
            ).count(),
            1,
        )
        self.assertEqual(
            ChatTurn.objects.filter(
                conversation=self.conversation,
                status=ChatTurn.Status.IN_PROGRESS,
            ).count(),
            1,
        )


    def test_acceptance_waits_for_conversation_row_lock(self):
        lock_acquired = Event()
        release_lock = Event()
        acceptance_started = Event()

        request = self.build_request("Wait for the conversation lock.")

        def hold_conversation_lock():
            close_old_connections()
            try:
                from django.db import transaction

                with transaction.atomic():
                    Conversation.objects.select_for_update().get(pk=self.conversation.id)
                    lock_acquired.set()

                    if not release_lock.wait(timeout=10):
                        raise TimeoutError("Lock release was not signaled.")
            finally:
                close_old_connections()

        def attempt_acceptance():
            close_old_connections()
            try:
                acceptance_started.set()
                result = accept_generation(**request)
                return result
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            lock_future = executor.submit(hold_conversation_lock)

            try:
                self.assertTrue(lock_acquired.wait(timeout=5))

                acceptance_future = executor.submit(attempt_acceptance)

                try:
                    self.assertTrue(acceptance_started.wait(timeout=5))

                    # Acceptance must remain blocked while the first
                    # transaction owns the Conversation row lock.
                    with self.assertRaises(TimeoutError):
                        acceptance_future.result(timeout=0.3)

                finally:
                    release_lock.set()

                lock_future.result(timeout=5)
                result = acceptance_future.result(timeout=5)

            finally:
                release_lock.set()

        self.assertEqual(
            ChatTurn.objects.filter(conversation=self.conversation).count(),
            1,
        )
        self.assertEqual(
            GenerationSubmission.objects.filter(user=self.user).count(),
            1,
        )
        self.assertEqual(result.chat_turn.status, ChatTurn.Status.IN_PROGRESS)
