from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ImproperlyConfigured

from apps.ai.config import GeminiConfig
from apps.ai.contracts import ConversationMessage, GenerationRequest
from apps.conversations.context.instructions import build_system_instruction
from apps.conversations.models import ChatTurn, Message

from .execution_config import reconstruct_generation_config


@dataclass(frozen=True, slots=True)
class GenerationExecutionInput:
    request: GenerationRequest
    config: GeminiConfig


def build_generation_request(chat_turn: ChatTurn) -> GenerationRequest:
    """
    Reconstruct the exact accepted generation request from persisted state.

    Historical messages are restored in the order recorded on the ChatTurn.
    No history selection, token counting, or database writes occur here.
    """
    history_ids = chat_turn.selected_history_message_ids

    if not isinstance(history_ids, list):
        raise ImproperlyConfigured(
            "ChatTurn selected history IDs must be a list."
        )

    parsed_ids = []

    for value in history_ids:
        if not isinstance(value, str):
            raise ImproperlyConfigured(
                "ChatTurn contains an invalid historical message ID."
            )

        try:
            parsed_id = UUID(value)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ImproperlyConfigured(
                "ChatTurn contains an invalid historical message ID."
            ) from exc

        if str(parsed_id) != value:
            raise ImproperlyConfigured(
                "ChatTurn historical message IDs must use canonical UUID format."
            )

        parsed_ids.append(parsed_id)

    if len(parsed_ids) != len(set(parsed_ids)):
        raise ImproperlyConfigured(
            "ChatTurn contains duplicate historical message IDs."
        )

    if len(parsed_ids) % 2 != 0:
        raise ImproperlyConfigured(
            "ChatTurn history must contain complete user-assistant pairs."
        )

    if chat_turn.user_message_id in parsed_ids:
        raise ImproperlyConfigured(
            "ChatTurn current user message cannot also be historical."
        )

    historical_messages = list(
        Message.objects.filter(id__in=parsed_ids).select_related(
            "user_chat_turn",
            "assistant_chat_turn",
        )
    )

    messages_by_id = {
        message.id: message
        for message in historical_messages
    }

    if len(messages_by_id) != len(parsed_ids):
        raise ImproperlyConfigured(
            "ChatTurn references missing historical messages."
        )

    ordered_messages = []

    for index in range(0, len(parsed_ids), 2):
        user_message = messages_by_id.get(parsed_ids[index])
        assistant_message = messages_by_id.get(parsed_ids[index + 1])

        if user_message is None or assistant_message is None:
            raise ImproperlyConfigured(
                "ChatTurn references missing historical messages."
            )

        if (
            user_message.conversation_id != chat_turn.conversation_id
            or assistant_message.conversation_id != chat_turn.conversation_id
        ):
            raise ImproperlyConfigured(
                "ChatTurn history contains messages from another conversation."
            )

        if (
            user_message.role != Message.Role.USER
            or assistant_message.role != Message.Role.ASSISTANT
        ):
            raise ImproperlyConfigured(
                "ChatTurn history contains an invalid message sequence."
            )

        try:
            user_turn = user_message.user_chat_turn
            assistant_turn = assistant_message.assistant_chat_turn
        except ChatTurn.DoesNotExist as exc:
            raise ImproperlyConfigured(
                "Historical messages are not associated with a ChatTurn."
            ) from exc

        if (
            user_turn.id != assistant_turn.id
            or user_turn.id == chat_turn.id
            or user_turn.status != ChatTurn.Status.COMPLETED
            or user_turn.conversation_id != chat_turn.conversation_id
            or user_turn.user_message_id != user_message.id
            or user_turn.assistant_message_id != assistant_message.id
        ):
            raise ImproperlyConfigured(
                "Historical messages do not form a valid completed exchange."
            )

        ordered_messages.extend((user_message, assistant_message))

    try:
        current_user_message = chat_turn.user_message
    except Message.DoesNotExist as exc:
        raise ImproperlyConfigured(
            "ChatTurn current user message is missing."
        ) from exc

    if (
        current_user_message.conversation_id != chat_turn.conversation_id
        or current_user_message.role != Message.Role.USER
        or not isinstance(current_user_message.content, str)
        or not current_user_message.content.strip()
    ):
        raise ImproperlyConfigured(
            "ChatTurn current user message is invalid."
        )

    platform_version = chat_turn.system_instruction_version
    platform_snapshot = chat_turn.system_instruction_snapshot
    custom_snapshot = chat_turn.custom_instruction_snapshot

    if (
        not isinstance(platform_version, str)
        or not platform_version
        or platform_version != platform_version.strip()
    ):
        raise ImproperlyConfigured(
            "ChatTurn platform instruction version is invalid."
        )

    if (
        not isinstance(platform_snapshot, str)
        or not platform_snapshot.strip()
    ):
        raise ImproperlyConfigured(
            "ChatTurn platform instruction snapshot is invalid."
        )

    if custom_snapshot is not None and (
        not isinstance(custom_snapshot, str)
        or not custom_snapshot.strip()
    ):
        raise ImproperlyConfigured(
            "ChatTurn custom instruction snapshot is invalid."
        )

    conversation_messages = tuple(
        ConversationMessage(
            role=message.role,
            content=message.content,
        )
        for message in (*ordered_messages, current_user_message)
    )

    system_instruction = build_system_instruction(
        platform_snapshot,
        custom_snapshot,
    )

    return GenerationRequest(
        messages=conversation_messages,
        system_instruction=system_instruction,
    )



def prepare_generation_execution(
    chat_turn: ChatTurn,
) -> GenerationExecutionInput:
    """Reconstruct and validate all persisted inputs before provider execution."""
    request = build_generation_request(chat_turn)
    config = reconstruct_generation_config(chat_turn)

    return GenerationExecutionInput(
        request=request,
        config=config,
    )
