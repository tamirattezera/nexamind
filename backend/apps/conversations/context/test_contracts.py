import uuid
from dataclasses import FrozenInstanceError

from django.test import SimpleTestCase

from apps.ai.contracts import ConversationMessage

from .contracts import PreparedConversationContext


class PreparedConversationContextTests(SimpleTestCase):
    def setUp(self):
        self.current_message_id = uuid.uuid4()
        self.history_ids = (uuid.uuid4(), uuid.uuid4())
        self.eligible_history_ids = (
            *self.history_ids,
            uuid.uuid4(),
            uuid.uuid4(),
        )

        self.prepared = PreparedConversationContext(
            current_message_id=self.current_message_id,
            messages=(
                ConversationMessage(
                    role="user",
                    content="Earlier question",
                ),
                ConversationMessage(
                    role="assistant",
                    content="Earlier answer",
                ),
                ConversationMessage(
                    role="user",
                    content="Current question",
                ),
            ),
            system_instruction="Platform instruction\\n\\nCustom instruction",
            platform_instruction_version="v1",
            platform_instruction_snapshot="Platform instruction",
            custom_instruction_snapshot="Custom instruction",
            eligible_history_message_ids=self.eligible_history_ids,
            selected_history_message_ids=self.history_ids,
            input_tokens=1200,
            max_input_tokens=32768,
        )

    def test_stores_current_message_identity(self):
        self.assertEqual(
            self.prepared.current_message_id,
            self.current_message_id,
        )

    def test_stores_ordered_provider_neutral_messages(self):
        self.assertEqual(
            self.prepared.messages,
            (
                ConversationMessage("user", "Earlier question"),
                ConversationMessage("assistant", "Earlier answer"),
                ConversationMessage("user", "Current question"),
            ),
        )

    def test_stores_instruction_snapshots_separately(self):
        self.assertEqual(
            self.prepared.platform_instruction_snapshot,
            "Platform instruction",
        )
        self.assertEqual(
            self.prepared.custom_instruction_snapshot,
            "Custom instruction",
        )

    def test_stores_eligible_and_selected_history_ids_separately(self):
        self.assertEqual(
            self.prepared.eligible_history_message_ids,
            self.eligible_history_ids,
        )
        self.assertEqual(
            self.prepared.selected_history_message_ids,
            self.history_ids,
        )
        self.assertIsInstance(
            self.prepared.eligible_history_message_ids,
            tuple,
        )
        self.assertIsInstance(
            self.prepared.selected_history_message_ids,
            tuple,
        )
        self.assertGreater(
            len(self.prepared.eligible_history_message_ids),
            len(self.prepared.selected_history_message_ids),
        )

    def test_stores_token_count_and_budget(self):
        self.assertEqual(self.prepared.input_tokens, 1200)
        self.assertEqual(self.prepared.max_input_tokens, 32768)

    def test_configuration_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.prepared.input_tokens = 1500

    def test_message_contract_is_also_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.prepared.messages[0].content = "Changed"
