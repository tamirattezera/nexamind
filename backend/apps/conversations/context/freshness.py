from apps.conversations.models import Message

from .contracts import PreparedConversationContext
from .instructions import build_system_instruction, normalize_custom_instruction


def is_context_snapshot_fresh(
    *,
    prepared_context: PreparedConversationContext,
    current_user_message: Message,
    platform_instruction_version: str,
    platform_instruction: str,
    custom_instruction: str | None,
    eligible_history_message_ids: tuple,
) -> bool:
    """
    Compare prepared context metadata with the current conversation state.

    This function performs no database queries and no provider operations.
    """
    if prepared_context.current_message_id != current_user_message.id:
        return False

    if not prepared_context.messages:
        return False

    current_provider_message = prepared_context.messages[-1]

    if (
        current_provider_message.role != Message.Role.USER
        or current_provider_message.content != current_user_message.content
    ):
        return False

    if (
        prepared_context.platform_instruction_version
        != platform_instruction_version
    ):
        return False

    if prepared_context.platform_instruction_snapshot != platform_instruction:
        return False

    normalized_custom_instruction = normalize_custom_instruction(
        custom_instruction
    )

    expected_system_instruction = build_system_instruction(
        platform_instruction,
        normalized_custom_instruction,
    )

    if prepared_context.system_instruction != expected_system_instruction:
        return False

    if (
        prepared_context.custom_instruction_snapshot
        != normalized_custom_instruction
    ):
        return False

    if (
        prepared_context.eligible_history_message_ids
        != tuple(eligible_history_message_ids)
    ):
        return False

    return True
