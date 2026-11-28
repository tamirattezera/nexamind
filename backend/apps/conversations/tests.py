import uuid
from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from django.utils import timezone

from .models import ChatTurn, Conversation, Message
from .pagination import (
    CURSOR_SALT,
    InvalidMessageCursor,
    MessageCursorPagination,
    decode_message_cursor,
    encode_message_cursor,
)
from .serializers import ConversationSerializer
from .instructions.platform import (
    PLATFORM_INSTRUCTION_VERSION,
    PLATFORM_SYSTEM_INSTRUCTION,
)
from .models import (
    ChatTurn,
    Conversation,
    GenerationSubmission,
    Message,
)

User = get_user_model()


class ConversationSerializerTests(TestCase):
    """Tests for conversation serialization and input validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="serializer@example.com",
            password="StrongTestPassword123!",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongTestPassword123!",
        )

    def test_serializes_conversation_fields(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Learning Django",
            custom_instructions="Explain step by step.",
        )

        serializer = ConversationSerializer(conversation)

        self.assertEqual(
            set(serializer.data.keys()),
            {
                "id",
                "user",
                "title",
                "custom_instructions",
                "created_at",
                "updated_at",
            },
        )

        self.assertEqual(serializer.data["title"], "Learning Django")

    def test_accepts_valid_conversation_data(self):
        data = {
            "title": "Learning DRF",
            "custom_instructions": "Use practical examples.",
        }

        serializer = ConversationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        conversation = serializer.save(user=self.user)

        self.assertEqual(conversation.user, self.user)
        self.assertEqual(conversation.title, "Learning DRF")

    def test_client_cannot_override_conversation_owner(self):
        data = {
            "user": self.other_user.pk,
            "title": "My private conversation",
        }

        serializer = ConversationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        conversation = serializer.save(user=self.user)

        self.assertEqual(conversation.user, self.user)
        self.assertNotEqual(conversation.user, self.other_user)

    def test_client_cannot_override_server_managed_fields(self):
        forged_id = uuid.uuid4()

        data = {
            "id": str(forged_id),
            "user": self.other_user.pk,
            "title": "Server-managed fields test",
            "created_at": "2000-01-01T00:00:00Z",
            "updated_at": "2000-01-01T00:00:00Z",
        }

        serializer = ConversationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertNotIn("id", serializer.validated_data)
        self.assertNotIn("user", serializer.validated_data)
        self.assertNotIn("created_at", serializer.validated_data)
        self.assertNotIn("updated_at", serializer.validated_data)

        conversation = serializer.save(user=self.user)

        self.assertNotEqual(conversation.id, forged_id)
        self.assertEqual(conversation.user, self.user)

    def test_rejects_invalid_titles(self):
        invalid_titles = ["", "   ", "A" * 256]

        for title in invalid_titles:
            with self.subTest(title=repr(title)):
                serializer = ConversationSerializer(data={"title": title})

                self.assertFalse(serializer.is_valid())
                self.assertIn("title", serializer.errors)


class ConversationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongTestPassword123!",
        )

    def test_conversation_generates_uuid_primary_key(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Learning Django",
        )

        self.assertIsInstance(conversation.id, uuid.UUID)

    def test_each_conversation_has_a_unique_uuid(self):
        first = Conversation.objects.create(
            user=self.user,
            title="First conversation",
        )

        second = Conversation.objects.create(
            user=self.user,
            title="Second conversation",
        )

        self.assertNotEqual(first.id, second.id)

    def test_conversation_belongs_to_its_owner(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="My private conversation",
        )

        self.assertEqual(conversation.user, self.user)
        self.assertEqual(conversation.user_id, self.user.id)

    def test_user_can_access_its_conversations(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="My conversation",
        )

        self.assertIn(
            conversation,
            self.user.conversations.all(),
        )

    def test_users_only_see_their_own_conversations(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongTestPassword123!",
        )

        conversation = Conversation.objects.create(
            user=self.user,
            title="Private conversation",
        )

        self.assertIn(conversation, self.user.conversations.all())
        self.assertNotIn(conversation, other_user.conversations.all())

    def test_conversation_stores_title_and_custom_instructions(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Learning Django",
            custom_instructions="Explain concepts step by step.",
        )

        self.assertEqual(conversation.title, "Learning Django")
        self.assertEqual(
            conversation.custom_instructions,
            "Explain concepts step by step.",
        )

    def test_custom_instructions_can_be_null(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Conversation without instructions",
        )

        self.assertIsNone(conversation.custom_instructions)

    def test_custom_instructions_can_be_empty(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Conversation with empty instructions",
            custom_instructions="",
        )

        self.assertEqual(conversation.custom_instructions, "")

    def test_created_at_is_set_automatically(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Timestamp test",
        )

        self.assertIsNotNone(conversation.created_at)

    def test_updated_at_is_set_automatically(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Update timestamp test",
        )

        self.assertIsNotNone(conversation.updated_at)

    def test_updated_at_changes_when_conversation_is_saved(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Original title",
        )

        original_updated_at = conversation.updated_at

        conversation.updated_at = timezone.now() - timedelta(days=1)
        conversation.title = "Updated title"
        conversation.save()

        self.assertGreater(
            conversation.updated_at,
            original_updated_at,
        )

    def test_database_rejects_whitespace_only_title(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Conversation.objects.create(
                    user=self.user,
                    title="   ",
                )

    def test_database_rejects_empty_title(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Conversation.objects.create(
                    user=self.user,
                    title="",
                )

    def test_deleting_user_deletes_its_conversations(self):
        conversation = Conversation.objects.create(
            user=self.user,
            title="Conversation to delete",
        )

        conversation_id = conversation.id

        self.user.delete()
        self.assertFalse(Conversation.objects.filter(id=conversation_id).exists())

    def test_conversation_accepts_maximum_title_length(self):
        title = "A" * 255

        conversation = Conversation.objects.create(
            user=self.user,
            title=title,
        )

        self.assertEqual(len(conversation.title), 255)

    def test_conversation_rejects_title_longer_than_maximum(self):
        title = "A" * 256

        conversation = Conversation(
            user=self.user,
            title=title,
        )

        with self.assertRaises(ValidationError):
            conversation.full_clean()


class ConversationListCreateAPITests(APITestCase):
    """Tests for listing and creating conversations through the API."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="api@example.com",
            password="StrongTestPassword123!",
        )

        self.other_user = User.objects.create_user(
            email="other-api@example.com",
            password="StrongTestPassword123!",
        )

        self.url = "/api/v1/conversations/"

    def test_unauthenticated_user_cannot_list_conversations(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_create_conversation(self):
        response = self.client.post(
            self.url,
            {"title": "Unauthorized conversation"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_only_sees_own_conversations(self):
        own_conversation = Conversation.objects.create(
            user=self.user,
            title="My conversation",
        )

        Conversation.objects.create(
            user=self.other_user,
            title="Other user's conversation",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            str(own_conversation.id),
        )
        self.assertEqual(
            response.data[0]["title"],
            "My conversation",
        )

    def test_authenticated_user_can_create_conversation(self):
        payload = {
            "title": "Learning Django REST Framework",
            "custom_instructions": "Explain step by step.",
            "user": self.other_user.pk,
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        conversation = Conversation.objects.get(title="Learning Django REST Framework")

        self.assertEqual(conversation.user, self.user)
        self.assertNotEqual(conversation.user, self.other_user)
        self.assertEqual(
            response.data["custom_instructions"],
            "Explain step by step.",
        )

    def test_user_receives_empty_list_when_no_own_conversations(self):
        Conversation.objects.create(
            user=self.other_user,
            title="Another user's conversation",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class MessageModelTests(TestCase):
    """Tests for message model behavior and database constraints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="message@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Message model testing",
        )

    def test_message_generates_uuid_primary_key(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Hello, NexaMind!",
        )

        self.assertIsInstance(message.id, uuid.UUID)

    def test_each_message_has_a_unique_uuid(self):
        first = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="First message",
        )

        second = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="Second message",
        )

        self.assertNotEqual(first.id, second.id)

    def test_message_accepts_all_valid_roles(self):
        for role in Message.Role.values:
            with self.subTest(role=role):
                message = Message.objects.create(
                    conversation=self.conversation,
                    role=role,
                    content=f"Message with role {role}",
                )

                self.assertEqual(message.role, role)

    def test_message_belongs_to_its_conversation(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Testing conversation relationship",
        )

        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(
            message.conversation_id,
            self.conversation.id,
        )

    def test_conversation_exposes_its_messages(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Testing reverse relationship",
        )

        self.assertIn(message, self.conversation.messages.all())

    def test_message_stores_content_and_role(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="This is an assistant response.",
        )

        self.assertEqual(message.content, "This is an assistant response.")
        self.assertEqual(message.role, Message.Role.ASSISTANT)

    def test_created_at_is_set_automatically(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Timestamp test",
        )

        self.assertIsNotNone(message.created_at)

    def test_messages_are_ordered_by_created_at_and_id(self):
        first = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="First",
        )

        second = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="Second",
        )

        shared_timestamp = timezone.now()

        Message.objects.filter(id__in=[first.id, second.id]).update(
            created_at=shared_timestamp
        )

        messages = list(Message.objects.filter(conversation=self.conversation))

        expected_ids = sorted([first.id, second.id])
        actual_ids = [message.id for message in messages]

        self.assertEqual(actual_ids, expected_ids)

    def test_database_rejects_invalid_role(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    conversation=self.conversation,
                    role="invalid",
                    content="Invalid role test",
                )

    def test_database_rejects_whitespace_only_content(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    conversation=self.conversation,
                    role=Message.Role.USER,
                    content="   \n\t  ",
                )

    def test_deleting_conversation_deletes_its_messages(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Message to cascade delete",
        )

        message_id = message.id

        self.conversation.delete()

        self.assertFalse(Message.objects.filter(id=message_id).exists())

    def test_message_does_not_have_updated_at_field(self):
        field_names = [field.name for field in Message._meta.get_fields()]

        self.assertNotIn("updated_at", field_names)


class ConversationDetailAPITests(APITestCase):
    """Tests for retrieving, updating, and deleting conversations."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="detail@example.com",
            password="StrongTestPassword123!",
        )

        self.other_user = User.objects.create_user(
            email="other-detail@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="My private conversation",
            custom_instructions="Explain step by step.",
        )

        self.url = f"/api/v1/conversations/{self.conversation.id}/"

    def test_owner_can_retrieve_own_conversation(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["id"],
            str(self.conversation.id),
        )
        self.assertEqual(
            response.data["title"],
            "My private conversation",
        )

    def test_other_user_cannot_retrieve_conversation(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_user_cannot_retrieve_conversation(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_owner_can_partially_update_conversation(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"title": "Updated conversation title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.conversation.refresh_from_db()

        self.assertEqual(
            self.conversation.title,
            "Updated conversation title",
        )
        self.assertEqual(self.conversation.user, self.user)

    def test_other_user_cannot_update_conversation(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            self.url,
            {"title": "Unauthorized modification"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.conversation.refresh_from_db()

        self.assertEqual(
            self.conversation.title,
            "My private conversation",
        )
        self.assertEqual(self.conversation.user, self.user)

    def test_owner_can_delete_conversation(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(Conversation.objects.filter(id=self.conversation.id).exists())

    def test_other_user_cannot_delete_conversation(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(Conversation.objects.filter(id=self.conversation.id).exists())

    def test_unauthenticated_user_cannot_update_conversation(self):
        response = self.client.patch(
            self.url,
            {"title": "Unauthorized update"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.conversation.refresh_from_db()

        self.assertEqual(
            self.conversation.title,
            "My private conversation",
        )

    def test_unauthenticated_user_cannot_delete_conversation(self):
        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertTrue(Conversation.objects.filter(id=self.conversation.id).exists())


class ChatTurnModelTests(TestCase):
    """Tests for ChatTurn model behavior and database constraints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="chatturn@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="ChatTurn integrity tests",
        )

    def create_user_message(self, conversation=None):
        return Message.objects.create(
            conversation=conversation or self.conversation,
            role="user",
            content="Explain database constraints.",
        )

    def create_assistant_message(self, conversation=None):
        return Message.objects.create(
            conversation=conversation or self.conversation,
            role="assistant",
            content="A database constraint protects data integrity.",
        )

    def create_turn(self, **overrides):
        defaults = {
            "conversation": self.conversation,
            "user_message": self.create_user_message(),
            "idempotency_key": uuid.uuid4(),
            "request_hash": "a" * 64,
            "system_instruction_version": "v1",
            "system_instruction_snapshot": "You are a helpful assistant.",
        }
        defaults.update(overrides)

        return ChatTurn.objects.create(**defaults)

    def test_creates_valid_in_progress_turn(self):
        turn = self.create_turn()

        self.assertEqual(turn.status, ChatTurn.Status.IN_PROGRESS)
        self.assertIsNone(turn.assistant_message)
        self.assertIsNone(turn.completed_at)
        self.assertIsNone(turn.error_code)
        self.assertIsNone(turn.error_message)

    def test_creates_valid_completed_turn(self):
        assistant_message = self.create_assistant_message()

        turn = self.create_turn(
            status=ChatTurn.Status.COMPLETED,
            assistant_message=assistant_message,
            completed_at=timezone.now(),
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        self.assertEqual(turn.status, ChatTurn.Status.COMPLETED)
        self.assertEqual(turn.assistant_message, assistant_message)
        self.assertIsNotNone(turn.completed_at)

    def test_creates_valid_failed_turn(self):
        turn = self.create_turn(
            status=ChatTurn.Status.FAILED,
            completed_at=timezone.now(),
            error_code="PROVIDER_TIMEOUT",
        )

        self.assertEqual(turn.status, ChatTurn.Status.FAILED)
        self.assertIsNone(turn.assistant_message)
        self.assertEqual(turn.error_code, "PROVIDER_TIMEOUT")
        self.assertIsNone(turn.error_message)

    def test_rejects_execution_claim_id_without_claimed_at(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(execution_claim_id=uuid.uuid4())

    def test_rejects_execution_claimed_at_without_claim_id(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(execution_claimed_at=timezone.now())

    def test_rejects_invalid_request_hash(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(request_hash="not-a-valid-sha256")

    def test_rejects_completed_turn_without_assistant_message(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(
                    status=ChatTurn.Status.COMPLETED,
                    completed_at=timezone.now(),
                )

    def test_rejects_failed_turn_without_error_code(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(
                    status=ChatTurn.Status.FAILED,
                    completed_at=timezone.now(),
                )

    def test_rejects_duplicate_idempotency_key_in_same_conversation(self):
        idempotency_key = uuid.uuid4()

        self.create_turn(idempotency_key=idempotency_key)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(idempotency_key=idempotency_key)

    def test_rejects_second_in_progress_turn_in_same_conversation(self):
        self.create_turn()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn()

    def test_allows_same_idempotency_key_in_different_conversations(self):
        idempotency_key = uuid.uuid4()

        self.create_turn(idempotency_key=idempotency_key)

        other_conversation = Conversation.objects.create(
            user=self.user,
            title="Another conversation",
        )

        turn = self.create_turn(
            conversation=other_conversation,
            idempotency_key=idempotency_key,
        )

        self.assertEqual(turn.idempotency_key, idempotency_key)
        self.assertNotEqual(
            turn.conversation_id,
            self.conversation.id,
        )

    def test_rejects_negative_token_usage(self):
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            with self.subTest(field=field):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self.create_turn(**{field: -1})

    def test_rejects_invalid_status(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(status="UNKNOWN")

    def test_rejects_in_progress_turn_with_failure_information(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(error_code="PROVIDER_ERROR")

    def test_rejects_failed_turn_with_assistant_message(self):
        assistant_message = self.create_assistant_message()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(
                    status=ChatTurn.Status.FAILED,
                    assistant_message=assistant_message,
                    completed_at=timezone.now(),
                    error_code="PROVIDER_ERROR",
                )

    def test_rejects_completed_turn_with_failure_information(self):
        assistant_message = self.create_assistant_message()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(
                    status=ChatTurn.Status.COMPLETED,
                    assistant_message=assistant_message,
                    completed_at=timezone.now(),
                    error_code="PROVIDER_ERROR",
                )

    def test_user_message_can_belong_to_only_one_chat_turn(self):
        user_message = self.create_user_message()

        first_assistant = self.create_assistant_message()
        self.create_turn(
            user_message=user_message,
            status=ChatTurn.Status.COMPLETED,
            assistant_message=first_assistant,
            completed_at=timezone.now(),
        )

        second_assistant = self.create_assistant_message()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(
                    user_message=user_message,
                    status=ChatTurn.Status.COMPLETED,
                    assistant_message=second_assistant,
                    completed_at=timezone.now(),
                )

    def test_assistant_message_can_belong_to_only_one_chat_turn(self):
        assistant_message = self.create_assistant_message()

        self.create_turn(
            status=ChatTurn.Status.COMPLETED,
            assistant_message=assistant_message,
            completed_at=timezone.now(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_turn(
                    status=ChatTurn.Status.COMPLETED,
                    assistant_message=assistant_message,
                    completed_at=timezone.now(),
                )


class GenerationSubmissionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="generation@example.com",
            password="StrongTestPassword123!",
        )

    def test_generates_uuid_primary_key(self):
        submission = GenerationSubmission.objects.create(
            user=self.user,
        )

        self.assertIsInstance(submission.id, uuid.UUID)

    def test_belongs_to_authenticated_user(self):
        submission = GenerationSubmission.objects.create(
            user=self.user,
        )

        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.user_id, self.user.id)

    def test_created_at_is_set_automatically(self):
        submission = GenerationSubmission.objects.create(
            user=self.user,
        )

        self.assertIsNotNone(submission.created_at)

    def test_is_independent_of_conversations(self):
        submission = GenerationSubmission.objects.create(
            user=self.user,
        )

        conversation = Conversation.objects.create(
            user=self.user,
            title="Temporary conversation",
        )

        conversation.delete()

        self.assertTrue(
            GenerationSubmission.objects.filter(
                id=submission.id,
            ).exists()
        )


class MessageCursorCodecTests(TestCase):
    """Tests for signed message pagination cursors."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="cursor@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Cursor testing",
        )
        self.message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Test message",
        )

    def test_cursor_round_trip_preserves_message_boundary(self):
        token = encode_message_cursor(
            self.conversation.id,
            self.message,
        )

        timestamp, message_id = decode_message_cursor(
            token,
            self.conversation.id,
        )

        self.assertEqual(timestamp, self.message.created_at)
        self.assertEqual(message_id, self.message.id)

    def test_rejects_cursor_for_another_conversation(self):
        token = encode_message_cursor(
            self.conversation.id,
            self.message,
        )
        another_conversation_id = uuid.uuid4()

        with self.assertRaises(InvalidMessageCursor):
            decode_message_cursor(token, another_conversation_id)

    def test_rejects_tampered_cursor(self):
        token = encode_message_cursor(
            self.conversation.id,
            self.message,
        )

        with self.assertRaises(InvalidMessageCursor):
            decode_message_cursor(
                token + "tampered",
                self.conversation.id,
            )

    def test_rejects_expired_cursor(self):
        payload = {
            "version": 1,
            "conversation_id": str(self.conversation.id),
            "created_at": self.message.created_at.isoformat(),
            "message_id": str(self.message.id),
        }

        with patch("django.core.signing.time.time", return_value=1):
            expired_token = signing.dumps(
                payload,
                salt=CURSOR_SALT,
            )

        with self.assertRaises(InvalidMessageCursor):
            decode_message_cursor(
                expired_token,
                self.conversation.id,
            )

    def test_rejects_invalid_message_uuid_in_signed_payload(self):
        payload = {
            "version": 1,
            "conversation_id": str(self.conversation.id),
            "created_at": self.message.created_at.isoformat(),
            "message_id": "not-a-uuid",
        }
        token = signing.dumps(payload, salt=CURSOR_SALT)

        with self.assertRaises(InvalidMessageCursor):
            decode_message_cursor(token, self.conversation.id)

    def test_rejects_unsupported_cursor_version(self):
        payload = {
            "version": 2,
            "conversation_id": str(self.conversation.id),
            "created_at": self.message.created_at.isoformat(),
            "message_id": str(self.message.id),
        }
        token = signing.dumps(payload, salt=CURSOR_SALT)

        with self.assertRaises(InvalidMessageCursor):
            decode_message_cursor(token, self.conversation.id)

    def test_rejects_non_dictionary_payload(self):
        token = signing.dumps(
            ["unexpected", "payload"],
            salt=CURSOR_SALT,
        )

        with self.assertRaises(InvalidMessageCursor):
            decode_message_cursor(token, self.conversation.id)


class MessageCursorPaginationTests(TestCase):
    """Tests for database-backed message cursor pagination."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pagination@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Pagination testing",
        )
        self.factory = APIRequestFactory()
        self.view = SimpleNamespace(kwargs={"id": str(self.conversation.id)})

    def create_messages(self, count, same_timestamp=False):
        messages = []

        for index in range(1, count + 1):
            messages.append(
                Message.objects.create(
                    id=uuid.UUID(int=index),
                    conversation=self.conversation,
                    role=Message.Role.USER,
                    content=f"Message {index}",
                )
            )

        if same_timestamp and messages:
            common_timestamp = timezone.now()
            Message.objects.filter(conversation=self.conversation).update(
                created_at=common_timestamp
            )

        return list(Message.objects.filter(conversation=self.conversation))

    def paginate(self, params=None, paginator=None):
        request = Request(self.factory.get("/", data=params or {}))
        paginator = paginator or MessageCursorPagination()
        page = paginator.paginate_queryset(
            Message.objects.filter(conversation=self.conversation),
            request,
            view=self.view,
        )
        return paginator, page

    def test_default_page_size_is_thirty(self):
        self.create_messages(31)

        paginator, page = self.paginate()

        self.assertEqual(len(page), 30)
        self.assertTrue(paginator.has_more)
        self.assertIsNotNone(paginator.next_cursor)

    def test_first_page_returns_newest_messages_chronologically(self):
        self.create_messages(5, same_timestamp=True)

        paginator, page = self.paginate({"page_size": "2"})

        self.assertEqual(
            [message.id for message in page],
            [uuid.UUID(int=4), uuid.UUID(int=5)],
        )
        self.assertTrue(paginator.has_more)

    def test_subsequent_pages_do_not_duplicate_or_skip_messages(self):
        self.create_messages(5, same_timestamp=True)

        first_paginator, first_page = self.paginate({"page_size": "2"})
        first_ids = [message.id for message in first_page]

        second_paginator, second_page = self.paginate(
            {
                "page_size": "2",
                "cursor": first_paginator.next_cursor,
            }
        )
        second_ids = [message.id for message in second_page]

        third_paginator, third_page = self.paginate(
            {
                "page_size": "2",
                "cursor": second_paginator.next_cursor,
            }
        )
        third_ids = [message.id for message in third_page]

        # Each page is chronological, but pages arrive newest first.
        self.assertEqual(
            first_ids,
            [uuid.UUID(int=4), uuid.UUID(int=5)],
        )
        self.assertEqual(
            second_ids,
            [uuid.UUID(int=2), uuid.UUID(int=3)],
        )
        self.assertEqual(
            third_ids,
            [uuid.UUID(int=1)],
        )

        all_ids = first_ids + second_ids + third_ids

        # Every message appears exactly once across all pages.
        self.assertEqual(
            sorted(all_ids),
            [uuid.UUID(int=i) for i in range(1, 6)],
        )
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertFalse(third_paginator.has_more)
        self.assertIsNone(third_paginator.next_cursor)

    def test_empty_queryset_returns_empty_page(self):
        paginator, page = self.paginate()

        self.assertEqual(page, [])
        self.assertFalse(paginator.has_more)
        self.assertIsNone(paginator.next_cursor)

    def test_exact_page_size_has_no_next_cursor(self):
        self.create_messages(2)

        paginator, page = self.paginate({"page_size": "2"})

        self.assertEqual(len(page), 2)
        self.assertFalse(paginator.has_more)
        self.assertIsNone(paginator.next_cursor)

    def test_rejects_invalid_page_sizes(self):
        invalid_values = [
            "0",
            "101",
            "abc",
            "+2",
            " 2 ",
            "2.0",
            "٢",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(DRFValidationError):
                    self.paginate({"page_size": value})

    def test_rejects_invalid_cursor(self):
        with self.assertRaises(DRFValidationError):
            self.paginate(
                {
                    "cursor": "not-a-valid-cursor",
                }
            )

    def test_paginated_response_has_approved_structure(self):
        self.create_messages(3)

        paginator, page = self.paginate({"page_size": "2"})
        response = paginator.get_paginated_response(
            [
                {
                    "id": str(message.id),
                    "content": message.content,
                }
                for message in page
            ]
        )

        self.assertEqual(
            set(response.data.keys()),
            {"results", "next", "has_more"},
        )
        self.assertTrue(response.data["has_more"])
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(len(response.data["results"]), 2)


class MessageListAPITests(APITestCase):
    """Tests for retrieving conversation messages through the API."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="message-list@example.com",
            password="StrongTestPassword123!",
        )
        self.other_user = User.objects.create_user(
            email="other-message-list@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="My message history",
        )
        self.other_conversation = Conversation.objects.create(
            user=self.other_user,
            title="Another user's message history",
        )

        self.url = f"/api/v1/conversations/{self.conversation.id}/messages/"

    def create_message(self, conversation, role, content):
        return Message.objects.create(
            conversation=conversation,
            role=role,
            content=content,
        )

    def test_unauthenticated_user_cannot_list_messages(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_owner_can_retrieve_own_messages(self):
        first = self.create_message(
            self.conversation,
            Message.Role.USER,
            "Hello, NexaMind!",
        )
        second = self.create_message(
            self.conversation,
            Message.Role.ASSISTANT,
            "Hello! How can I help?",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {"results", "next", "has_more"},
        )
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(first.id), str(second.id)],
        )

    def test_message_response_contains_exact_read_only_fields(self):
        message = self.create_message(
            self.conversation,
            Message.Role.USER,
            "Explain cursor pagination.",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data["results"][0].keys()),
            {"id", "role", "content", "created_at"},
        )
        self.assertEqual(
            response.data["results"][0]["id"],
            str(message.id),
        )
        self.assertEqual(
            response.data["results"][0]["role"],
            Message.Role.USER,
        )
        self.assertEqual(
            response.data["results"][0]["content"],
            message.content,
        )

    def test_other_user_cannot_retrieve_messages(self):
        self.create_message(
            self.conversation,
            Message.Role.USER,
            "Private message",
        )

        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_cannot_retrieve_messages_from_own_url_for_other_conversation(self):
        self.create_message(
            self.other_conversation,
            Message.Role.USER,
            "Another user's private message",
        )

        other_url = f"/api/v1/conversations/" f"{self.other_conversation.id}/messages/"

        self.client.force_authenticate(user=self.user)

        response = self.client.get(other_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_missing_conversation_returns_404(self):
        missing_url = (
            "/api/v1/conversations/" "00000000-0000-0000-0000-000000000001/messages/"
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(missing_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_owner_can_retrieve_older_message_page(self):
        messages = []

        for index in range(1, 4):
            messages.append(
                Message.objects.create(
                    id=uuid.UUID(int=index),
                    conversation=self.conversation,
                    role=Message.Role.USER,
                    content=f"Message {index}",
                )
            )

        # Force a deterministic ordering boundary.
        common_timestamp = timezone.now()
        Message.objects.filter(conversation=self.conversation).update(
            created_at=common_timestamp
        )

        self.client.force_authenticate(user=self.user)

        first_response = self.client.get(
            self.url,
            {"page_size": 2},
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(first_response.data["has_more"])

        cursor = first_response.data["next"]

        second_response = self.client.get(
            self.url,
            {"page_size": 2, "cursor": cursor},
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(second_response.data["has_more"])
        self.assertEqual(
            [item["id"] for item in second_response.data["results"]],
            [str(messages[0].id)],
        )

    def test_empty_conversation_returns_empty_paginated_results(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])
        self.assertIsNone(response.data["next"])
        self.assertFalse(response.data["has_more"])


class PlatformInstructionTests(TestCase):
    """Tests for the versioned platform system instruction."""

    def test_platform_instruction_version_is_defined(self):
        self.assertIsInstance(PLATFORM_INSTRUCTION_VERSION, str)
        self.assertTrue(PLATFORM_INSTRUCTION_VERSION.strip())

    def test_platform_instruction_is_nonempty(self):
        self.assertIsInstance(PLATFORM_SYSTEM_INSTRUCTION, str)
        self.assertTrue(PLATFORM_SYSTEM_INSTRUCTION.strip())

    def test_platform_instruction_defines_general_purpose_identity(self):
        self.assertIn("general-purpose AI assistant", PLATFORM_SYSTEM_INSTRUCTION)
        self.assertIn("programming", PLATFORM_SYSTEM_INSTRUCTION)
        self.assertIn("writing", PLATFORM_SYSTEM_INSTRUCTION)
        self.assertIn("learning", PLATFORM_SYSTEM_INSTRUCTION)

    def test_platform_instruction_defines_security_boundaries(self):
        normalized_instruction = " ".join(PLATFORM_SYSTEM_INSTRUCTION.split())

        required_phrases = (
            "untrusted input",
            "application security boundaries",
            "API keys",
            "another user's conversations",
        )

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_instruction)

    def test_platform_instruction_has_no_outer_whitespace(self):
        self.assertEqual(
            PLATFORM_SYSTEM_INSTRUCTION,
            PLATFORM_SYSTEM_INSTRUCTION.strip(),
        )


class ConversationDetailLockingTests(TransactionTestCase):
    """Verify conversation mutations acquire a PostgreSQL row lock."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="locking@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Conversation for locking tests",
            custom_instructions="Be precise.",
        )
        self.url = f"/api/v1/conversations/{self.conversation.id}/"

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def get_conversation_lock_queries(self, captured_queries):
        table_name = Conversation._meta.db_table.upper()

        return [
            query["sql"]
            for query in captured_queries
            if (
                "FOR UPDATE" in query["sql"].upper()
                and table_name in query["sql"].upper()
            )
        ]

    def test_patch_acquires_conversation_row_lock(self):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.patch(
                self.url,
                {"title": "Updated title"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.get_conversation_lock_queries(captured))

    def test_put_acquires_conversation_row_lock(self):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.put(
                self.url,
                {
                    "title": "Replaced title",
                    "custom_instructions": "Use concise explanations.",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.get_conversation_lock_queries(captured))

    def test_delete_acquires_conversation_row_lock(self):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertTrue(self.get_conversation_lock_queries(captured))

    def test_get_does_not_acquire_conversation_row_lock(self):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.get_conversation_lock_queries(captured))
