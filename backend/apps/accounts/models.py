from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# Create your models here.
class UserManager(BaseUserManager):
    """Manager for email-based user accounts."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        email = self.normalize_email(email or "").strip().lower()
        if not email:
            raise ValueError("An email address is required.")
        if not password:
            raise ValueError("A password is required.")

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()