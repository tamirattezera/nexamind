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
