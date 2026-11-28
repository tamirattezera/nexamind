from dataclasses import dataclass

from apps.conversations.models import ChatTurn


@dataclass(frozen=True, slots=True)
class AcceptedGeneration:
    """A newly accepted generation that may proceed to the provider."""

    chat_turn: ChatTurn


@dataclass(frozen=True, slots=True)
class ReplayedGeneration:
    """An existing generation request matched by its idempotency key."""

    chat_turn: ChatTurn
