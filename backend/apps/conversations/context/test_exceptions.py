from django.test import SimpleTestCase

from .exceptions import ContextChanged, ContextSnapshotStale


class ContextSnapshotExceptionTests(SimpleTestCase):
    def test_snapshot_stale_is_an_internal_exception(self):
        error = ContextSnapshotStale("Snapshot no longer matches.")

        self.assertIsInstance(error, Exception)
        self.assertNotEqual(
            getattr(error, "error_code", None),
            "CHAT_CONTEXT_CHANGED",
        )

    def test_context_changed_has_approved_error_code(self):
        error = ContextChanged()

        self.assertEqual(error.error_code, "CHAT_CONTEXT_CHANGED")

    def test_context_changed_has_safe_public_message(self):
        error = ContextChanged()

        self.assertEqual(
            str(error),
            "Conversation context changed repeatedly. Please retry your request.",
        )
