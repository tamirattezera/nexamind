import uuid
from dataclasses import replace

from django.test import SimpleTestCase

from apps.ai.contracts import ConversationMessage
from apps.conversations.models import Message

from .contracts import PreparedConversationContext
from .freshness import is_context_snapshot_fresh


class ContextSnapshotFreshnessTests(SimpleTestCase):
    def setUp(self):
        self.current_message = Message(
            id=uuid.uuid4(),
            role=Message.Role.USER,
            content="Current question",
        )

        self.history_ids = (uuid.uuid4(), uuid.uuid4())

        self.prepared = PreparedConversationContext(
            current_message_id=self.current_message.id,
            messages=(
                ConversationMessage("user", "Earlier question"),
                ConversationMessage("assistant", "Earlier answer"),
                ConversationMessage("user", "Current question"),
            ),
            system_instruction="Platform instruction",
            platform_instruction_version="v1",
            platform_instruction_snapshot="Platform instruction",
            custom_instruction_snapshot=None,
            eligible_history_message_ids=self.history_ids,
            selected_history_message_ids=self.history_ids,
            input_tokens=100,
            max_input_tokens=1000,
        )

        self.current_state = {
            "prepared_context": self.prepared,
            "current_user_message": self.current_message,
            "platform_instruction_version": "v1",
            "platform_instruction": "Platform instruction",
            "custom_instruction": None,
            "eligible_history_message_ids": self.history_ids,
        }

    def test_accepts_unchanged_snapshot(self):
        self.assertTrue(
            is_context_snapshot_fresh(**self.current_state)
        )

    def test_rejects_different_current_message_id(self):
        message = Message(
            id=uuid.uuid4(),
            role=Message.Role.USER,
            content="Current question",
        )

        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "current_user_message": message,
                }
            )
        )

    def test_rejects_changed_current_message_content(self):
        message = Message(
            id=self.current_message.id,
            role=Message.Role.USER,
            content="Changed question",
        )

        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "current_user_message": message,
                }
            )
        )

    def test_rejects_changed_platform_instruction_version(self):
        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "platform_instruction_version": "v2",
                }
            )
        )

    def test_rejects_changed_platform_instruction_content(self):
        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "platform_instruction": "Changed instruction",
                }
            )
        )

    def test_rejects_changed_custom_instruction(self):
        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "custom_instruction": "Be concise",
                }
            )
        )

    def test_normalizes_blank_custom_instruction(self):
        self.assertTrue(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "custom_instruction": "  \n ",
                }
            )
        )

    def test_rejects_changed_history_ids(self):
        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "eligible_history_message_ids": (
                        self.history_ids[1],
                        self.history_ids[0],
                    ),
                }
            )
        )

    def test_rejects_added_history_message(self):
        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "eligible_history_message_ids": (
                        *self.history_ids,
                        uuid.uuid4(),
                    ),
                }
            )
        )

    def test_rejects_inconsistent_system_instruction(self):
        prepared = replace(
            self.prepared,
            system_instruction="Unexpected system instruction",
        )

        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "prepared_context": prepared,
                }
            )
        )

    def test_accepts_unchanged_custom_instruction_snapshot(self):
        prepared = replace(
            self.prepared,
            system_instruction="Platform instruction\n\nBe concise",
            custom_instruction_snapshot="Be concise",
        )

        self.assertTrue(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "prepared_context": prepared,
                    "custom_instruction": "Be concise",
                }
            )
        )

    def test_rejects_empty_prepared_messages(self):
        prepared = PreparedConversationContext(
            **{
                **{
                    field: getattr(self.prepared, field)
                    for field in self.prepared.__dataclass_fields__
                },
                "messages": (),
            }
        )

        self.assertFalse(
            is_context_snapshot_fresh(
                **{
                    **self.current_state,
                    "prepared_context": prepared,
                }
            )
        )
