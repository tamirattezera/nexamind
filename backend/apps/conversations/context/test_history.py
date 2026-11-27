import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import ChatTurn, Conversation, Message

from .history import get_eligible_history_messages, MAX_HISTORY_CANDIDATES

User = get_user_model()


class EligibleHistoryMessageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="history@example.com",
            password="StrongTestPassword123!",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            title="History selector tests",
        )

    def create_message(self, role, content, conversation=None):
        return Message.objects.create(
            conversation=conversation or self.conversation,
            role=role,
            content=content,
        )

    def create_turn(
        self,
        user_message,
        status=ChatTurn.Status.IN_PROGRESS,
        assistant_message=None,
    ):
        completed_at = (
            timezone.now()
            if status in (ChatTurn.Status.COMPLETED, ChatTurn.Status.FAILED)
            else None
        )

        return ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            idempotency_key=uuid.uuid4(),
            request_hash="a" * 64,
            status=status,
            completed_at=completed_at,
            error_code=(
                "PROVIDER_TIMEOUT" if status == ChatTurn.Status.FAILED else None
            ),
            system_instruction_version="v1",
            system_instruction_snapshot="You are a helpful assistant.",
        )

    def create_completed_turn(self, content):
        user_message = self.create_message(
            Message.Role.USER,
            f"User: {content}",
        )
        assistant_message = self.create_message(
            Message.Role.ASSISTANT,
            f"Assistant: {content}",
        )

        self.create_turn(
            user_message,
            status=ChatTurn.Status.COMPLETED,
            assistant_message=assistant_message,
        )

        return user_message, assistant_message

    def test_includes_both_messages_from_completed_turns(self):
        user_message, assistant_message = self.create_completed_turn(
            "completed exchange"
        )
        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertEqual(result, (user_message, assistant_message))

    def test_excludes_in_progress_turn(self):
        user_message = self.create_message(
            Message.Role.USER,
            "Unfinished request",
        )
        self.create_turn(user_message)

        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertEqual(result, ())

    def test_excludes_failed_turn(self):
        user_message = self.create_message(
            Message.Role.USER,
            "Failed request",
        )
        self.create_turn(
            user_message,
            status=ChatTurn.Status.FAILED,
        )

        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertEqual(result, ())

    def test_excludes_messages_without_chat_turns(self):
        user_message = self.create_message(
            Message.Role.USER,
            "Unlinked user message",
        )
        assistant_message = self.create_message(
            Message.Role.ASSISTANT,
            "Unlinked assistant message",
        )

        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertEqual(result, ())
        self.assertNotIn(user_message, result)
        self.assertNotIn(assistant_message, result)

    def test_excludes_system_messages(self):
        system_message = self.create_message(
            Message.Role.SYSTEM,
            "System content",
        )
        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertEqual(result, ())
        self.assertNotIn(system_message, result)

    def test_excludes_current_user_message(self):
        current_message = self.create_message(
            Message.Role.USER,
            "Current question",
        )
        self.create_turn(current_message)

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertNotIn(current_message, result)

    def test_returns_messages_in_chronological_order(self):
        first_user, first_assistant = self.create_completed_turn("first")
        second_user, second_assistant = self.create_completed_turn("second")

        base_time = timezone.now() - timedelta(minutes=10)

        for index, message in enumerate(
            (first_user, first_assistant, second_user, second_assistant)
        ):
            Message.objects.filter(pk=message.pk).update(
                created_at=base_time + timedelta(seconds=index)
            )

        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertEqual(
            result,
            (
                first_user,
                first_assistant,
                second_user,
                second_assistant,
            ),
        )

    def test_limits_candidates_before_eligibility_filtering(self):
        oldest_user, oldest_assistant = self.create_completed_turn(
            "oldest completed exchange"
        )

        base_time = timezone.now() - timedelta(minutes=10)

        Message.objects.filter(pk=oldest_user.pk).update(created_at=base_time)
        Message.objects.filter(pk=oldest_assistant.pk).update(
            created_at=base_time + timedelta(seconds=1)
        )

        for index in range(MAX_HISTORY_CANDIDATES):
            message = self.create_message(
                Message.Role.USER,
                f"Recent failed request {index}",
            )
            self.create_turn(
                message,
                status=ChatTurn.Status.FAILED,
            )
            Message.objects.filter(pk=message.pk).update(
                created_at=base_time + timedelta(minutes=1, seconds=index)
            )

        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        # The two oldest completed messages fall outside the latest
        # 100 candidates. The 100 newer failed messages are then filtered.
        self.assertEqual(result, ())

    def test_excludes_completed_turn_split_by_candidate_boundary(self):
        user_message, assistant_message = self.create_completed_turn(
            "exchange split by candidate boundary"
        )

        base_time = timezone.now() - timedelta(minutes=10)

        Message.objects.filter(pk=user_message.pk).update(
            created_at=base_time
        )
        Message.objects.filter(pk=assistant_message.pk).update(
            created_at=base_time + timedelta(seconds=1)
        )

        # These 99 newer messages push the user message outside
        # the latest 100 candidates while the assistant remains inside.
        for index in range(MAX_HISTORY_CANDIDATES - 1):
            message = self.create_message(
                Message.Role.USER,
                f"Recent unlinked message {index}",
            )
            Message.objects.filter(pk=message.pk).update(
                created_at=base_time + timedelta(minutes=1, seconds=index)
            )

        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        result = get_eligible_history_messages(
            self.conversation,
            current_message,
        )

        self.assertNotIn(user_message, result)
        self.assertNotIn(assistant_message, result)


    def test_retrieves_history_with_one_database_query(self):
        self.create_completed_turn("query efficiency")
        current_message = Message(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Current question",
        )

        with self.assertNumQueries(1):
            result = get_eligible_history_messages(
                self.conversation,
                current_message,
            )

        self.assertEqual(len(result), 2)
