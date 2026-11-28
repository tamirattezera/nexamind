import hashlib
import uuid

from django.test import SimpleTestCase

from .idempotency import hash_message_content, parse_idempotency_key


class ParseIdempotencyKeyTests(SimpleTestCase):
    def test_accepts_valid_uuid_v4(self):
        expected = uuid.uuid4()

        result = parse_idempotency_key(str(expected))

        self.assertEqual(result, expected)
        self.assertEqual(result.version, 4)

    def test_accepts_uppercase_uuid_v4(self):
        expected = uuid.uuid4()

        result = parse_idempotency_key(str(expected).upper())

        self.assertEqual(result, expected)

    def test_rejects_invalid_uuid(self):
        with self.assertRaises(ValueError):
            parse_idempotency_key("not-a-uuid")

    def test_rejects_uuid_version_other_than_four(self):
        key = uuid.uuid1()

        with self.assertRaises(ValueError):
            parse_idempotency_key(str(key))

    def test_rejects_noncanonical_uuid_representation(self):
        key = uuid.uuid4()

        with self.assertRaises(ValueError):
            parse_idempotency_key(key.hex)

    def test_rejects_non_string_value(self):
        with self.assertRaises(ValueError):
            parse_idempotency_key(None)


class HashMessageContentTests(SimpleTestCase):
    def test_returns_sha256_hex_digest(self):
        content = "Hello NexaMind"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result = hash_message_content(content)

        self.assertEqual(result, expected)
        self.assertEqual(len(result), 64)

    def test_same_content_produces_same_hash(self):
        first = hash_message_content("Hello NexaMind")
        second = hash_message_content("Hello NexaMind")

        self.assertEqual(first, second)

    def test_different_content_produces_different_hash(self):
        first = hash_message_content("Hello NexaMind")
        second = hash_message_content("Hello NexaMind!")

        self.assertNotEqual(first, second)

    def test_hashes_exact_input_without_normalizing_it(self):
        normalized = hash_message_content("Hello NexaMind")
        whitespace_changed = hash_message_content(" Hello NexaMind ")

        self.assertNotEqual(normalized, whitespace_changed)

    def test_rejects_non_string_content(self):
        with self.assertRaises(TypeError):
            hash_message_content(None)
