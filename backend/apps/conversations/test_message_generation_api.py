import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.providers.gemini import (
    ProviderError,
    ProviderTimeoutError,
)
from apps.conversations.idempotency import hash_message_content
from apps.conversations.models import ChatTurn, Conversation, Message
from apps.conversations.services.contracts import (
    AcceptedGeneration,
    ReplayedGeneration,
)
from apps.conversations.services.exceptions import (
    GenerationRateLimitExceeded,
)
from apps.ai.config import GeminiConfig
from apps.ai.contracts import ConversationMessage
from apps.conversations.context.contracts import PreparedConversationContext
from apps.conversations.instructions.platform import (
    PLATFORM_INSTRUCTION_VERSION,
    PLATFORM_SYSTEM_INSTRUCTION,
)

User = get_user_model()


class MessageGenerationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="generation-api@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Generation API tests",
        )
        self.url = f"/api/v1/conversations/{self.conversation.id}/messages/"
        self.client.force_authenticate(user=self.user)

    def create_turn(self, content, *, key=None, completed=False):
        key = key or uuid.uuid4()

        user_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content=content,
        )

        assistant_message = None
        fields = {}

        if completed:
            assistant_message = Message.objects.create(
                conversation=self.conversation,
                role=Message.Role.ASSISTANT,
                content="Persisted assistant response.",
            )
            fields = {
                "status": ChatTurn.Status.COMPLETED,
                "assistant_message": assistant_message,
                "model_name": "gemini-test-model",
                "input_tokens": 20,
                "output_tokens": 10,
                "total_tokens": 30,
                "completed_at": timezone.now(),
            }

        turn = ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=user_message,
            idempotency_key=key,
            request_hash=hash_message_content(content),
            system_instruction_version="v1",
            system_instruction_snapshot="Test system instruction.",
            **fields,
        )
        return turn

    def complete_turn(self, accepted):
        turn = accepted.chat_turn

        assistant_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="Generated assistant response.",
        )

        turn.assistant_message = assistant_message
        turn.model_name = "gemini-test-model"
        turn.input_tokens = 20
        turn.output_tokens = 10
        turn.total_tokens = 30
        turn.status = ChatTurn.Status.COMPLETED
        turn.completed_at = timezone.now()
        turn.save(
            update_fields=[
                "assistant_message",
                "model_name",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "status",
                "completed_at",
            ]
        )
        return turn

    def test_new_generation_returns_created_response(self):
        content = "Explain database transactions."
        key = uuid.uuid4()
        turn = self.create_turn(content, key=key)

        with (
            patch(
                "apps.conversations.services.orchestration.prepare_and_accept_generation",
                return_value=AcceptedGeneration(chat_turn=turn),
            ),
            patch(
                "apps.conversations.services.execution_service.execute_generation",
            ) as execute,
        ):
            execute.side_effect = self.complete_turn

            response = self.client.post(
                self.url,
                {"content": content},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(key),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        execute.assert_called_once()

    def test_completed_replay_returns_ok_without_execution(self):
        content = "Explain database transactions."
        key = uuid.uuid4()
        turn = self.create_turn(content, key=key, completed=True)

        with (
            patch(
                "apps.conversations.services.orchestration.prepare_and_accept_generation",
                return_value=ReplayedGeneration(chat_turn=turn),
            ),
            patch(
                "apps.conversations.services.execution_service.execute_generation",
            ) as execute,
        ):
            response = self.client.post(
                self.url,
                {"content": content},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(key),
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        execute.assert_not_called()

    def test_recovered_stale_turn_replay_returns_gateway_timeout(self):
        content = "Explain database transactions."
        key = uuid.uuid4()
        turn = self.create_turn(content, key=key)

        turn.status = ChatTurn.Status.FAILED
        turn.error_code = "CHAT_TURN_PROCESSING_TIMEOUT"
        turn.error_message = "Generation processing timed out."
        turn.completed_at = timezone.now()
        turn.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "completed_at",
            ]
        )

        with (
            patch(
                "apps.conversations.services.orchestration.prepare_and_accept_generation",
                return_value=ReplayedGeneration(chat_turn=turn),
            ),
            patch(
                "apps.conversations.services.execution_service.execute_generation",
            ) as execute,
        ):
            response = self.client.post(
                self.url,
                {"content": content},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(key),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_504_GATEWAY_TIMEOUT,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "CHAT_TURN_PROCESSING_TIMEOUT",
        )
        self.assertEqual(
            response.data["error"]["message"],
            "Generation processing timed out.",
        )
        execute.assert_not_called()

    def test_active_replay_returns_accepted_without_execution(self):
        content = "Explain database transactions."
        key = uuid.uuid4()
        turn = self.create_turn(content, key=key)

        with (
            patch(
                "apps.conversations.services.orchestration.prepare_and_accept_generation",
                return_value=ReplayedGeneration(chat_turn=turn),
            ),
            patch(
                "apps.conversations.services.execution_service.execute_generation",
            ) as execute,
        ):
            response = self.client.post(
                self.url,
                {"content": content},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(key),
            )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "processing")
        execute.assert_not_called()

    def test_generation_rate_limit_returns_too_many_requests_without_execution(self):
        with (
            patch(
                "apps.conversations.services.orchestration.prepare_and_accept_generation",
                side_effect=GenerationRateLimitExceeded(),
            ),
            patch(
                "apps.conversations.services.execution_service.execute_generation",
            ) as execute,
        ):
            response = self.client.post(
                self.url,
                {"content": "Explain database transactions."},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "RATE_LIMIT_EXCEEDED",
        )
        self.assertEqual(
            response.data["error"]["message"],
            "The generation submission rate limit has been exceeded.",
        )
        execute.assert_not_called()

    def test_missing_idempotency_key_returns_bad_request(self):
        with patch(
            "apps.conversations.services.orchestration.prepare_and_accept_generation"
        ) as prepare:
            response = self.client.post(
                self.url,
                {"content": "Explain database transactions."},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"]["code"],
            "IDEMPOTENCY_KEY_REQUIRED",
        )
        prepare.assert_not_called()

    def test_invalid_idempotency_key_returns_bad_request(self):
        with patch(
            "apps.conversations.services.orchestration.prepare_and_accept_generation"
        ) as prepare:
            response = self.client.post(
                self.url,
                {"content": "Explain database transactions."},
                format="json",
                HTTP_IDEMPOTENCY_KEY="not-a-valid-uuid",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"]["code"],
            "IDEMPOTENCY_KEY_INVALID",
        )
        prepare.assert_not_called()

    def test_blank_content_returns_validation_error(self):
        with patch(
            "apps.conversations.services.orchestration.prepare_and_accept_generation"
        ) as prepare:
            response = self.client.post(
                self.url,
                {"content": "   "},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"]["code"],
            "VALIDATION_ERROR",
        )
        prepare.assert_not_called()

    def test_unauthenticated_post_returns_401(self):
        self.client.force_authenticate(user=None)

        with patch(
            "apps.conversations.services.orchestration.prepare_and_accept_generation"
        ) as prepare:
            response = self.client.post(
                self.url,
                {"content": "Explain database transactions."},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "AUTHENTICATION_REQUIRED",
        )
        prepare.assert_not_called()

    def test_user_cannot_submit_to_another_users_conversation(self):
        another_user = User.objects.create_user(
            email="another-generation-api@example.com",
            password="StrongTestPassword123!",
        )
        another_conversation = Conversation.objects.create(
            user=another_user,
            title="Private conversation",
        )
        another_url = f"/api/v1/conversations/{another_conversation.id}/messages/"

        response = self.client.post(
            another_url,
            {"content": "Explain database transactions."},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "RESOURCE_NOT_FOUND",
        )
        self.assertEqual(
            Message.objects.filter(
                conversation=another_conversation,
            ).count(),
            0,
        )
        self.assertEqual(
            ChatTurn.objects.filter(
                conversation=another_conversation,
            ).count(),
            0,
        )

    def test_provider_failures_return_expected_http_responses(self):
        failure_cases = (
            (
                ProviderTimeoutError("simulated timeout"),
                status.HTTP_504_GATEWAY_TIMEOUT,
                "AI_PROVIDER_TIMEOUT",
            ),
            (
                ProviderError("simulated provider failure"),
                status.HTTP_502_BAD_GATEWAY,
                "AI_PROVIDER_ERROR",
            ),
            (
                ImproperlyConfigured("simulated configuration failure"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_SERVER_ERROR",
            ),
            (
                RuntimeError("simulated unexpected failure"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_SERVER_ERROR",
            ),
        )

        for index, (exception, expected_status, expected_code) in enumerate(
            failure_cases,
            start=1,
        ):
            with self.subTest(error_code=expected_code):
                content = f"Provider failure test {index}."
                key = uuid.uuid4()
                turn = self.create_turn(content, key=key)

                execution_input = SimpleNamespace(
                    request=object(),
                    config=object(),
                )

                with (
                    patch(
                        "apps.conversations.services.orchestration.prepare_and_accept_generation",
                        return_value=AcceptedGeneration(chat_turn=turn),
                    ),
                    patch(
                        "apps.conversations.services.execution_service.prepare_generation_execution",
                        return_value=execution_input,
                        side_effect=(
                            exception
                            if isinstance(exception, ImproperlyConfigured)
                            else None
                        ),
                    ),
                    patch(
                        "apps.conversations.services.execution_service.generate_response",
                        side_effect=exception,
                    ) as generate,
                ):
                    response = self.client.post(
                        self.url,
                        {"content": content},
                        format="json",
                        HTTP_IDEMPOTENCY_KEY=str(key),
                    )

                self.assertEqual(
                    response.status_code,
                    expected_status,
                    msg=f"Unexpected response: {response.data!r}",
                )
                self.assertEqual(
                    response.data["error"]["code"],
                    expected_code,
                )

                turn.refresh_from_db()
                self.assertEqual(turn.status, ChatTurn.Status.FAILED)
                self.assertEqual(turn.error_code, expected_code)
                self.assertIsNone(turn.assistant_message_id)

                if isinstance(
                    exception,
                    (ProviderTimeoutError, ProviderError, RuntimeError),
                ):
                    generate.assert_called_once()
                else:
                    generate.assert_not_called()

    def test_different_submission_while_turn_active_returns_conflict(self):
        active_key = uuid.uuid4()

        self.create_turn(
            "First request.",
            key=active_key,
        )

        generation_config = GeminiConfig(
            api_key="test-secret-api-key",
            model="gemini-test-model",
            thinking_level="LOW",
            max_output_tokens=4096,
            timeout_ms=30000,
        )

        def build_context(
            *,
            conversation,
            current_user_message,
            generation_config,
        ):
            return PreparedConversationContext(
                current_message_id=current_user_message.id,
                messages=(
                    ConversationMessage(
                        role="user",
                        content=current_user_message.content,
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

        with (
            patch(
                "apps.conversations.services.orchestration.get_gemini_config",
                return_value=generation_config,
            ),
            patch(
                "apps.conversations.services.orchestration.prepare_conversation_context",
                side_effect=build_context,
            ),
        ):
            response = self.client.post(
                self.url,
                {"content": "Second request."},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
            msg=f"Unexpected response: {response.data!r}",
        )
        self.assertEqual(
            response.data["error"]["code"],
            "CHAT_TURN_ALREADY_IN_PROGRESS",
        )

        self.assertEqual(
            Message.objects.filter(conversation=self.conversation).count(),
            1,
        )
        self.assertEqual(
            ChatTurn.objects.filter(conversation=self.conversation).count(),
            1,
        )

    def test_reused_idempotency_key_with_different_content_returns_conflict(self):
        key = uuid.uuid4()

        self.create_turn(
            "Original content.",
            key=key,
        )

        response = self.client.post(
            self.url,
            {"content": "Different content."},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(key),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "IDEMPOTENCY_KEY_REUSED",
        )

        self.assertEqual(
            Message.objects.filter(conversation=self.conversation).count(),
            1,
        )
        self.assertEqual(
            ChatTurn.objects.filter(conversation=self.conversation).count(),
            1,
        )
