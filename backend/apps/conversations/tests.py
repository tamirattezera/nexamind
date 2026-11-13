import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone

from .models import Conversation
from .serializers import ConversationSerializer

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
