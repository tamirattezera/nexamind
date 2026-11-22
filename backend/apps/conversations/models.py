import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=False,
    )
    title = models.CharField(max_length=255)
    custom_instructions = models.TextField(
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "-updated_at"],
                name="conv_user_updated_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=~models.Q(title__regex=r"^\s*$"),
                name="conv_title_not_blank",
            ),
        ]

    def __str__(self):
        return self.title


class Message(models.Model):
    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=False,
    )

    role = models.CharField(
        max_length=9,
        choices=Role.choices,
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

        indexes = [
            models.Index(
                fields=["conversation", "created_at", "id"],
                name="msg_conv_created_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["system", "user", "assistant"]),
                name="msg_role_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(content__regex=r"^\s*$"),
                name="msg_content_not_blank",
            ),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
