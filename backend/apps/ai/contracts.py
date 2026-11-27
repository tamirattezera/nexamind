from dataclasses import dataclass
from typing import Literal


MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    messages: tuple[ConversationMessage, ...]
    system_instruction: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    model_name: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    thinking_tokens: int | None
    finish_reason: str | None
    response_id: str | None


@dataclass(frozen=True, slots=True)
class TokenCountRequest:
    messages: tuple[ConversationMessage, ...]
    system_instruction: str


@dataclass(frozen=True, slots=True)
class TokenCountResult:
    total_tokens: int
