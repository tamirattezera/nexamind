import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.conversations.models import ChatTurn, Conversation, Message

from .execution import (
    GenerationExecutionInput,
    build_generation_request,
    prepare_generation_execution,
)

User = get_user_model()


class BuildGenerationRequestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="execution@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Execution reconstruction tests",
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
        turn = ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            idempotency_key=uuid.uuid4(),
            request_hash="a" * 64,
            status=ChatTurn.Status.COMPLETED,
            completed_at=timezone.now(),
            system_instruction_version="platform-v1",
            system_instruction_snapshot="Historical instruction",
        )
        return turn, user_message, assistant_message

    def create_current_turn(self, history_ids=None, **overrides):
        user_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )
        values = {
            "conversation": self.conversation,
            "user_message": user_message,
            "idempotency_key": uuid.uuid4(),
            "request_hash": "b" * 64,
            "status": ChatTurn.Status.IN_PROGRESS,
            "system_instruction_version": "platform-v2",
            "system_instruction_snapshot": "Current platform instruction",
            "custom_instruction_snapshot": "Be concise.",
            "selected_history_message_ids": (
                [] if history_ids is None else history_ids
            ),
        }
        values.update(overrides)
        return ChatTurn.objects.create(**values)

    def test_reconstructs_exact_persisted_history_order(self):
        first = self.create_completed_turn("first exchange")
        second = self.create_completed_turn("second exchange")
        turn = self.create_current_turn([
            str(first[1].id),
            str(first[2].id),
            str(second[1].id),
            str(second[2].id),
        ])

        request = build_generation_request(turn)

        self.assertEqual(
            [(m.role, m.content) for m in request.messages],
            [
                ("user", "User: first exchange"),
                ("assistant", "Assistant: first exchange"),
                ("user", "User: second exchange"),
                ("assistant", "Assistant: second exchange"),
                ("user", "Current question"),
            ],
        )
        self.assertEqual(
            request.system_instruction,
            "Current platform instruction\n\nBe concise.",
        )

    def test_reconstructs_request_without_history(self):
        turn = self.create_current_turn()
        request = build_generation_request(turn)

        self.assertEqual(
            [(m.role, m.content) for m in request.messages],
            [("user", "Current question")],
        )

    def test_uses_platform_instruction_without_custom_snapshot(self):
        turn = self.create_current_turn(custom_instruction_snapshot=None)

        request = build_generation_request(turn)

        self.assertEqual(
            request.system_instruction,
            "Current platform instruction",
        )

    def test_rejects_non_list_history(self):
        turn = self.create_current_turn(selected_history_message_ids="invalid")

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_non_string_history_id(self):
        turn = self.create_current_turn([123])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_invalid_uuid(self):
        turn = self.create_current_turn(["not-a-uuid"])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_noncanonical_uuid(self):
        _, user_message, assistant_message = self.create_completed_turn("case")
        turn = self.create_current_turn([
            str(user_message.id).upper(),
            str(assistant_message.id),
        ])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_duplicate_history_ids(self):
        _, user_message, _ = self.create_completed_turn("duplicate")
        turn = self.create_current_turn([
            str(user_message.id),
            str(user_message.id),
        ])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_odd_number_of_history_ids(self):
        _, user_message, _ = self.create_completed_turn("incomplete")
        turn = self.create_current_turn([str(user_message.id)])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_missing_historical_message(self):
        _, user_message, assistant_message = self.create_completed_turn("deleted")
        history_ids = [str(user_message.id), str(assistant_message.id)]
        assistant_message.delete()
        turn = self.create_current_turn(history_ids)

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_history_from_another_conversation(self):
        other = Conversation.objects.create(
            user=self.user,
            title="Other conversation",
        )
        user_message = Message.objects.create(
            conversation=other,
            role=Message.Role.USER,
            content="Other user message",
        )
        assistant_message = Message.objects.create(
            conversation=other,
            role=Message.Role.ASSISTANT,
            content="Other assistant message",
        )
        ChatTurn.objects.create(
            conversation=other,
            user_message=user_message,
            assistant_message=assistant_message,
            idempotency_key=uuid.uuid4(),
            request_hash="c" * 64,
            status=ChatTurn.Status.COMPLETED,
            completed_at=timezone.now(),
            system_instruction_version="platform-v1",
            system_instruction_snapshot="Instruction",
        )
        turn = self.create_current_turn([
            str(user_message.id),
            str(assistant_message.id),
        ])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_wrong_historical_role_order(self):
        _, user_message, assistant_message = self.create_completed_turn("wrong order")
        turn = self.create_current_turn([
            str(assistant_message.id),
            str(user_message.id),
        ])

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_current_message_from_another_conversation(self):
        other = Conversation.objects.create(
            user=self.user,
            title="Other current conversation",
        )
        other_message = Message.objects.create(
            conversation=other,
            role=Message.Role.USER,
            content="Wrong conversation",
        )
        turn = self.create_current_turn(user_message=other_message)

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_blank_custom_instruction_snapshot(self):
        turn = self.create_current_turn(custom_instruction_snapshot="  \n ")

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_blank_platform_instruction_snapshot(self):
        turn = self.create_current_turn(system_instruction_snapshot="  \n ")

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)

    def test_rejects_invalid_platform_instruction_version(self):
        turn = self.create_current_turn(
            system_instruction_version=" platform-v2 "
        )

        with self.assertRaises(ImproperlyConfigured):
            build_generation_request(turn)



class PrepareGenerationExecutionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="prepare-execution@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Execution preparation tests",
        )

    def create_current_turn(self, **overrides):
        user_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )
        values = {
            "conversation": self.conversation,
            "user_message": user_message,
            "idempotency_key": uuid.uuid4(),
            "request_hash": "d" * 64,
            "status": ChatTurn.Status.IN_PROGRESS,
            "system_instruction_version": "platform-v2",
            "system_instruction_snapshot": "Current platform instruction",
            "custom_instruction_snapshot": "Be concise.",
            "selected_history_message_ids": [],
        }
        values.update(overrides)
        return ChatTurn.objects.create(**values)

    def create_configured_turn(self, **overrides):
        values = {
            "generation_metadata": {
                "schema_version": 1,
                "provider": "gemini",
                "requested_model": "gemini-test-model",
                "thinking_level": "HIGH",
            },
            "max_output_tokens": 4096,
        }
        values.update(overrides)
        return self.create_current_turn(**values)

    @override_settings(
        GEMINI_API_KEY="test-api-key",
        GEMINI_TIMEOUT_MS=30000,
    )
    def test_returns_request_and_persisted_generation_configuration(self):
        turn = self.create_configured_turn()

        result = prepare_generation_execution(turn)

        self.assertIsInstance(result, GenerationExecutionInput)
        self.assertEqual(
            result.request.messages[-1].content,
            "Current question",
        )
        self.assertEqual(
            result.request.system_instruction,
            "Current platform instruction\n\nBe concise.",
        )
        self.assertEqual(result.config.api_key, "test-api-key")
        self.assertEqual(result.config.model, "gemini-test-model")
        self.assertEqual(result.config.thinking_level, "HIGH")
        self.assertEqual(result.config.max_output_tokens, 4096)
        self.assertEqual(result.config.timeout_ms, 30000)

    @override_settings(
        GEMINI_API_KEY="test-api-key",
        GEMINI_TIMEOUT_MS=30000,
    )
    def test_rejects_invalid_generation_metadata(self):
        turn = self.create_configured_turn(
            generation_metadata={
                "schema_version": 1,
                "provider": "unsupported",
                "requested_model": "gemini-test-model",
                "thinking_level": "HIGH",
            },
        )

        with self.assertRaises(ImproperlyConfigured):
            prepare_generation_execution(turn)

    @override_settings(
        GEMINI_API_KEY="",
        GEMINI_TIMEOUT_MS=30000,
    )
    def test_rejects_missing_server_api_key(self):
        turn = self.create_configured_turn()

        with self.assertRaises(ImproperlyConfigured):
            prepare_generation_execution(turn)
