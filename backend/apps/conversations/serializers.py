from rest_framework import serializers

from .models import Conversation, Message
from .message_config import get_conversation_message_config


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversation resources."""

    class Meta:
        model = Conversation
        fields = [
            "id",
            "user",
            "title",
            "custom_instructions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]


class MessageSerializer(serializers.ModelSerializer):
    """Read-only serializer for conversation messages."""

    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "created_at",
        ]
        read_only_fields = fields


class SendMessageSerializer(serializers.Serializer):
    """Validate user-submitted conversation messages."""

    content = serializers.CharField(trim_whitespace=True)

    def validate_content(self, value):
        config = get_conversation_message_config()

        if len(value) > config.max_message_length:
            raise serializers.ValidationError(
                f"Ensure this field has no more than "
                f"{config.max_message_length} characters."
            )

        return value
