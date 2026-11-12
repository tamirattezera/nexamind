from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from .serializers import RegistrationSerializer

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


class RegistrationSerializerTests(TestCase):
    """Tests for user registration serializer."""

    def test_register_user(self):
        data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        serializer = RegistrationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertEqual(user.email, "newuser@example.com")
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_confirmation_mismatch(self):
        data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }

        serializer = RegistrationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("password_confirm", serializer.errors)

    def test_rejects_common_password(self):
        data = {
            "email": "newuser@example.com",
            "password": "password",
            "password_confirm": "password",
        }

        serializer = RegistrationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_rejects_duplicate_email(self):
        User.objects.create_user(
            email="existing@example.com",
            password="ExistingPassword123!",
        )

        data = {
            "email": "existing@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        serializer = RegistrationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_client_cannot_assign_privileged_fields(self):
        data = {
            "email": "attacker@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "is_staff": True,
            "is_superuser": True,
        }

        serializer = RegistrationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_rejects_duplicate_email_with_different_case(self):
        User.objects.create_user(
            email="existing@example.com",
            password="ExistingPassword123!",
        )

        data = {
            "email": "EXISTING@EXAMPLE.COM",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        serializer = RegistrationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class RegistrationAPITests(APITestCase):
    """Tests for the user registration API endpoint."""

    def test_register_user_returns_created_response(self):
        data = {
            "email": "apiuser@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["email"], "apiuser@example.com")
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirm", response.data)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email="apiuser@example.com")

        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertNotEqual(user.password, "StrongPassword123!")

    def test_registration_rejects_password_mismatch(self):
        data = {
            "email": "mismatch@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_weak_password(self):
        data = {
            "email": "weak@example.com",
            "password": "password",
            "password_confirm": "password",
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            email="existing@example.com",
            password="ExistingPassword123!",
        )

        data = {
            "email": "existing@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_normalizes_email(self):
        data = {
            "email": "  NEWUSER@EXAMPLE.COM  ",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "newuser@example.com")
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_registration_rejects_privilege_escalation(self):
        data = {
            "email": "attacker@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "is_staff": True,
            "is_superuser": True,
        }

        response = self.client.post(
            "/api/v1/auth/register/",
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        user = User.objects.get(email="attacker@example.com")

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class JWTAuthenticationAPITests(APITestCase):
    """Tests for JWT authentication endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="login@example.com",
            password="StrongPassword123!",
        )

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "login@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_invalid_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "login@example.com",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_login_rejects_unknown_email(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "unknown@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_token_returns_new_access_token(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "login@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        refresh_token = login_response.data["refresh"]

        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_refresh_rotates_refresh_token(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "login@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        original_refresh = login_response.data["refresh"]

        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": original_refresh},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("refresh", response.data)
        self.assertNotEqual(response.data["refresh"], original_refresh)

    def test_rotated_refresh_token_cannot_be_reused(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "login@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        original_refresh = login_response.data["refresh"]

        first_refresh_response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": original_refresh},
            format="json",
        )

        self.assertEqual(first_refresh_response.status_code, 200)

        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": original_refresh},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_verify_valid_access_token(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "login@example.com",
                "password": "StrongPassword123!",
            },
            format="json",
        )

        access_token = login_response.data["access"]

        response = self.client.post(
            "/api/v1/auth/token/verify/",
            {"token": access_token},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_verify_invalid_access_token(self):
        response = self.client.post(
            "/api/v1/auth/token/verify/",
            {"token": "invalid.token.value"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
