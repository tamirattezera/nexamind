from apps.ai.contracts import ConversationMessage, TokenCountRequest
from apps.ai.services import count_tokens
from apps.conversations.instructions.platform import (
    PLATFORM_INSTRUCTION_VERSION,
    PLATFORM_SYSTEM_INSTRUCTION,
)
from apps.conversations.models import Conversation, Message

from .config import get_conversation_context_config
from .contracts import PreparedConversationContext
from .exceptions import ContextLimitExceeded
from .history import get_eligible_history_messages


def _build_system_instruction(
    platform_instruction: str,
    custom_instruction: str | None,
) -> str:
    if custom_instruction is None:
        return platform_instruction

    return f"{platform_instruction}\n\n{custom_instruction}"


def _to_conversation_message(message: Message) -> ConversationMessage:
    return ConversationMessage(
        role=message.role,
        content=message.content,
    )


def _count_input_tokens(
    messages: tuple[ConversationMessage, ...],
    system_instruction: str,
) -> int:
    result = count_tokens(
        TokenCountRequest(
            messages=messages,
            system_instruction=system_instruction,
        )
    )
    return result.total_tokens


def prepare_conversation_context(
    *,
    conversation: Conversation,
    current_user_message: Message,
) -> PreparedConversationContext:
    """
    Prepare immutable, token-bounded context without writing to the database.

    Historical messages are retained as complete user-assistant exchanges.
    The current user message is appended separately and need not be saved.
    """
    if current_user_message.role != Message.Role.USER:
        raise ValueError("The current conversation message must have the user role.")

    if current_user_message.conversation_id != conversation.id:
        raise ValueError(
            "The current user message must belong to the supplied conversation."
        )

    config = get_conversation_context_config()

    platform_instruction = PLATFORM_SYSTEM_INSTRUCTION
    custom_instruction = conversation.custom_instructions

    if custom_instruction is not None and not custom_instruction.strip():
        custom_instruction = None

    system_instruction = _build_system_instruction(
        platform_instruction,
        custom_instruction,
    )

    history = get_eligible_history_messages(
        conversation,
        current_user_message,
    )

    if len(history) % 2 != 0:
        raise RuntimeError(
            "Eligible conversation history must contain complete exchanges."
        )

    exchanges = tuple(
        (history[index], history[index + 1])
        for index in range(0, len(history), 2)
    )

    current_message = _to_conversation_message(current_user_message)

    def build_messages(
        selected_exchanges: tuple[tuple[Message, Message], ...],
    ) -> tuple[ConversationMessage, ...]:
        historical_messages = tuple(
            _to_conversation_message(message)
            for exchange in selected_exchanges
            for message in exchange
        )
        return (*historical_messages, current_message)

    all_messages = build_messages(exchanges)

    input_tokens = _count_input_tokens(
        all_messages,
        system_instruction,
    )

    if input_tokens <= config.max_input_tokens:
        selected_exchanges = exchanges

    else:
        mandatory_messages = (current_message,)

        mandatory_tokens = _count_input_tokens(
            mandatory_messages,
            system_instruction,
        )

        if mandatory_tokens > config.max_input_tokens:
            raise ContextLimitExceeded()

        # Binary search for the largest recent suffix of complete
        # exchanges that fits within the configured input budget.
        low = 0
        high = len(exchanges)
        selected_exchanges = ()
        input_tokens = mandatory_tokens

        while high - low > 1:
            middle = (low + high) // 2
            candidate_exchanges = exchanges[-middle:]
            candidate_messages = build_messages(candidate_exchanges)

            candidate_tokens = _count_input_tokens(
                candidate_messages,
                system_instruction,
            )

            if candidate_tokens <= config.max_input_tokens:
                low = middle
                selected_exchanges = candidate_exchanges
                input_tokens = candidate_tokens
            else:
                high = middle

    selected_history = tuple(
        message
        for exchange in selected_exchanges
        for message in exchange
    )

    return PreparedConversationContext(
        current_message_id=current_user_message.id,
        messages=build_messages(selected_exchanges),
        system_instruction=system_instruction,
        platform_instruction_version=PLATFORM_INSTRUCTION_VERSION,
        platform_instruction_snapshot=platform_instruction,
        custom_instruction_snapshot=custom_instruction,
        selected_history_message_ids=tuple(
            message.id for message in selected_history
        ),
        input_tokens=input_tokens,
        max_input_tokens=config.max_input_tokens,
    )
