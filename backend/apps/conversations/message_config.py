from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True, slots=True)
class ConversationMessageConfig:
    max_message_length: int


def get_conversation_message_config() -> ConversationMessageConfig:
    max_message_length = settings.CHAT_MAX_MESSAGE_LENGTH

    if max_message_length <= 0:
        raise ImproperlyConfigured(
            "CHAT_MAX_MESSAGE_LENGTH must be greater than zero."
        )

    return ConversationMessageConfig(
        max_message_length=max_message_length,
    )
