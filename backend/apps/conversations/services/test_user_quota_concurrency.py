import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

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
from .exceptions import GenerationRateLimitExceeded

User = get_user_model()


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentUserQuotaTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            email="quota-concurrency@example.com",
            password="StrongTestPassword123!",
        )
        self.conversations = [
            Conversation.objects.create(
                user=self.user,
                title=f"Quota conversation {index}",
            )
            for index in range(2)
        ]

    def build_request(self, conversation, content):
        message = Message(
            conversation=conversation,
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
            "conversation_id": conversation.id,
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
            except GenerationRateLimitExceeded:
                return ("rate_limited", None)
        finally:
            close_old_connections()

    @override_settings(
        CHAT_GENERATION_RATE_LIMIT=1,
        CHAT_GENERATION_RATE_WINDOW_SECONDS=60,
    )
    def test_concurrent_conversations_share_one_user_quota(self):
        requests = [
            self.build_request(
                self.conversations[0],
                "First conversation request.",
            ),
            self.build_request(
                self.conversations[1],
                "Second conversation request.",
            ),
        ]
        barrier = Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self.run_acceptance, barrier, request)
                for request in requests
            ]
            outcomes = [
                future.result(timeout=20)
                for future in futures
            ]

        self.assertCountEqual(
            [outcome[0] for outcome in outcomes],
            ["accepted", "rate_limited"],
        )
        self.assertEqual(
            GenerationSubmission.objects.filter(user=self.user).count(),
            1,
        )
        self.assertEqual(
            Message.objects.filter(
                conversation__in=self.conversations,
                role=Message.Role.USER,
            ).count(),
            1,
        )
        self.assertEqual(
            ChatTurn.objects.filter(
                conversation__in=self.conversations,
            ).count(),
            1,
        )
