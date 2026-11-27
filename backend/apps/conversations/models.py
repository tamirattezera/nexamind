import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


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


class ChatTurn(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="chat_turns",
        db_index=False,
    )

    user_message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="user_chat_turn",
    )

    assistant_message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="assistant_chat_turn",
        null=True,
        blank=True,
    )

    idempotency_key = models.UUIDField()

    request_hash = models.CharField(max_length=64)

    status = models.CharField(
        max_length=11,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )

    model_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )

    generation_metadata = models.JSONField(default=dict)

    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)

    effective_temperature = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )

    max_output_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    system_instruction_version = models.CharField(max_length=64)
    system_instruction_snapshot = models.TextField()

    custom_instruction_snapshot = models.TextField(
        null=True,
        blank=True,
    )

    selected_history_message_ids = models.JSONField(default=list)

    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "idempotency_key"],
                name="chatturn_conv_idem_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(request_hash__regex=r"^[0-9a-f]{64}$"),
                name="chatturn_request_hash_valid",
            ),
            models.UniqueConstraint(
                fields=["conversation"],
                condition=models.Q(status="IN_PROGRESS"),
                name="chatturn_one_active_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "IN_PROGRESS",
                        "COMPLETED",
                        "FAILED",
                    ]
                ),
                name="chatturn_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="IN_PROGRESS",
                        assistant_message__isnull=True,
                        completed_at__isnull=True,
                        error_code__isnull=True,
                        error_message__isnull=True,
                    )
                    | models.Q(
                        status="COMPLETED",
                        assistant_message__isnull=False,
                        completed_at__isnull=False,
                        error_code__isnull=True,
                        error_message__isnull=True,
                    )
                    | models.Q(
                        status="FAILED",
                        assistant_message__isnull=True,
                        completed_at__isnull=False,
                        error_code__isnull=False,
                    )
                ),
                name="chatturn_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(input_tokens__gte=0)
                | models.Q(input_tokens__isnull=True),
                name="chatturn_input_tokens_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(output_tokens__gte=0)
                | models.Q(output_tokens__isnull=True),
                name="chatturn_output_tokens_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(total_tokens__gte=0)
                | models.Q(total_tokens__isnull=True),
                name="chatturn_total_tokens_valid",
            ),
        ]

        indexes = [
            models.Index(
                fields=["conversation", "created_at"],
                name="chatturn_conv_created_idx",
            ),
            models.Index(
                fields=["status", "started_at"],
                name="chatturn_status_started_idx",
            ),
        ]

    def __str__(self):
        return f"ChatTurn {self.id} ({self.status})"
