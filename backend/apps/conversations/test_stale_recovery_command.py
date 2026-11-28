from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase


class RecoverStaleTurnsCommandTests(SimpleTestCase):
    @patch(
        "apps.conversations.management.commands.recover_stale_turns.recover_stale_turns"
    )
    def test_default_batch_size_and_zero_count(self, recover):
        recover.return_value = 0
        output = StringIO()

        call_command("recover_stale_turns", stdout=output)

        recover.assert_called_once_with(batch_size=100)
        self.assertEqual(output.getvalue(), "Recovered 0 stale ChatTurns.\n")

    @patch(
        "apps.conversations.management.commands.recover_stale_turns.recover_stale_turns"
    )
    def test_custom_batch_size_and_singular_output(self, recover):
        recover.return_value = 1
        output = StringIO()

        call_command("recover_stale_turns", batch_size=25, stdout=output)

        recover.assert_called_once_with(batch_size=25)
        self.assertEqual(output.getvalue(), "Recovered 1 stale ChatTurn.\n")

    def test_non_positive_batch_size_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command("recover_stale_turns", batch_size=0)
