import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import Conversation

User = get_user_model()


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
