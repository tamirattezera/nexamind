from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserManagerTests(TestCase):
    """Tests for the custom email-based user manager."""

    def test_create_user(self):
        user = User.objects.create_user(
            email="user@example.com", password="TestPassword123!"
        )

        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.check_password("TestPassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(
            email=" TAME@Example.COM ", password="TestPassword123!"
        )

        self.assertEqual(user.email, "tame@example.com")

    def test_create_user_requires_email(self):
        with self.assertRaisesMessage(ValueError, "An email address is required."):
            User.objects.create_user(email="", password="TestPassword123!")

    def test_create_user_requires_password(self):
        with self.assertRaisesMessage(ValueError, "A password is required."):
            User.objects.create_user(email="user@example.com", password="")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="AdminPassword123!"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.check_password("AdminPassword123!"))

    def test_create_superuser_requires_staff_status(self):
        with self.assertRaisesMessage(
            ValueError, "A superuser must have is_staff=True."
        ):
            User.objects.create_superuser(
                email="admin@example.com",
                password="AdminPassword123!",
                is_staff=False,
            )

    def test_create_superuser_requires_superuser_status(self):
        with self.assertRaisesMessage(
            ValueError, "A superuser must have is_superuser=True."
        ):
            User.objects.create_superuser(
                email="admin@example.com",
                password="AdminPassword123!",
                is_superuser=False,
            )
