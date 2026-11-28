import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone

from apps.conversations.models import ChatTurn, Conversation, Message
from apps.conversations.services.stale_recovery import recover_stale_turns


User = get_user_model()


class RecoverStaleTurnsTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="stale-recovery@example.com",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Stale recovery tests",
        )
        self.user_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Explain database recovery.",
        )
        self.chat_turn = self.create_turn(
            conversation=self.conversation,
            user_message=self.user_message,
        )

    def create_turn(self, *, conversation, user_message):
        return ChatTurn.objects.create(
            conversation=conversation,
            user_message=user_message,
            idempotency_key=uuid.uuid4(),
            request_hash="b" * 64,
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

    def make_claim(self, chat_turn, *, claimed_at):
        chat_turn.execution_claim_id = uuid.uuid4()
        chat_turn.execution_claimed_at = claimed_at
        chat_turn.save(
            update_fields=[
                "execution_claim_id",
                "execution_claimed_at",
            ]
        )

    def test_stale_unclaimed_turn_is_recovered(self):
        old_time = timezone.now() - timedelta(minutes=5)
        ChatTurn.objects.filter(pk=self.chat_turn.pk).update(
            started_at=old_time,
        )

        recovered = recover_stale_turns()

        self.chat_turn.refresh_from_db()
        self.assertEqual(recovered, 1)
        self.assertEqual(self.chat_turn.status, ChatTurn.Status.FAILED)
        self.assertEqual(
            self.chat_turn.error_code,
            "CHAT_TURN_PROCESSING_TIMEOUT",
        )
        self.assertEqual(
            self.chat_turn.error_message,
            "Generation processing timed out.",
        )
        self.assertIsNotNone(self.chat_turn.completed_at)
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)
        self.assertIsNone(self.chat_turn.assistant_message_id)
        self.assertTrue(
            Message.objects.filter(
                pk=self.user_message.pk,
                role=Message.Role.USER,
            ).exists()
        )

    def test_old_started_at_does_not_make_recently_claimed_turn_stale(self):
        now = timezone.now()
        old_start = now - timedelta(minutes=10)
        recent_claim = now - timedelta(seconds=30)

        self.chat_turn.started_at = old_start
        self.chat_turn.save(update_fields=["started_at"])
        self.make_claim(self.chat_turn, claimed_at=recent_claim)

        recovered = recover_stale_turns()

        self.chat_turn.refresh_from_db()
        self.assertEqual(recovered, 0)
        self.assertEqual(
            self.chat_turn.status,
            ChatTurn.Status.IN_PROGRESS,
        )
        self.assertIsNotNone(self.chat_turn.execution_claim_id)
        self.assertEqual(
            self.chat_turn.execution_claimed_at,
            recent_claim,
        )

    def test_stale_execution_claim_is_recovered(self):
        old_time = timezone.now() - timedelta(minutes=5)
        self.make_claim(self.chat_turn, claimed_at=old_time)

        recovered = recover_stale_turns()

        self.chat_turn.refresh_from_db()
        self.assertEqual(recovered, 1)
        self.assertEqual(self.chat_turn.status, ChatTurn.Status.FAILED)
        self.assertEqual(
            self.chat_turn.error_code,
            "CHAT_TURN_PROCESSING_TIMEOUT",
        )
        self.assertIsNone(self.chat_turn.execution_claim_id)
        self.assertIsNone(self.chat_turn.execution_claimed_at)

    def test_fresh_unclaimed_turn_is_not_recovered(self):
        self.chat_turn.started_at = timezone.now()
        self.chat_turn.save(update_fields=["started_at"])

        recovered = recover_stale_turns()

        self.chat_turn.refresh_from_db()
        self.assertEqual(recovered, 0)
        self.assertEqual(
            self.chat_turn.status,
            ChatTurn.Status.IN_PROGRESS,
        )
        self.assertIsNone(self.chat_turn.completed_at)

    def test_invalid_batch_size_is_rejected(self):
        for batch_size in (0, -1, 1.5, True, "100"):
            with self.subTest(batch_size=batch_size):
                with self.assertRaises(ValueError):
                    recover_stale_turns(batch_size=batch_size)
