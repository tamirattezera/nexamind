from rest_framework import serializers

from .models import Conversation


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
