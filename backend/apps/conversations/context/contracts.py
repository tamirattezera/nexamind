from dataclasses import dataclass
from uuid import UUID

from apps.ai.contracts import ConversationMessage


@dataclass(frozen=True, slots=True)
class PreparedConversationContext:
    current_message_id: UUID
    messages: tuple[ConversationMessage, ...]
    system_instruction: str
    platform_instruction_version: str
    platform_instruction_snapshot: str
    custom_instruction_snapshot: str | None
    selected_history_message_ids: tuple[UUID, ...]
    input_tokens: int
    max_input_tokens: int
