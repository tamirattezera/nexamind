from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True, slots=True)
class ConversationContextConfig:
    max_input_tokens: int


def get_conversation_context_config() -> ConversationContextConfig:
    max_input_tokens = settings.CHAT_CONTEXT_MAX_INPUT_TOKENS

    if max_input_tokens <= 0:
        raise ImproperlyConfigured(
            "CHAT_CONTEXT_MAX_INPUT_TOKENS must be greater than zero."
        )

    return ConversationContextConfig(
        max_input_tokens=max_input_tokens,
    )
