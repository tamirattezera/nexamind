from django.db import transaction

from apps.conversations.models import ChatTurn, Conversation
from apps.conversations.services.contracts import ReplayedGeneration
from apps.conversations.services.exceptions import IdempotencyKeyReused


@transaction.atomic
def find_idempotent_replay(
    *,
    user,
    conversation_id,
    idempotency_key,
    request_hash,
):
    """
    Find an existing idempotent request before context preparation.

    The Conversation lock preserves the established lock order and
    serializes this lookup with generation acceptance.
    """
    conversation = (
        Conversation.objects
        .select_for_update()
        .get(pk=conversation_id)
    )

    # Do not reveal whether another user's conversation exists.
    if conversation.user_id != user.pk:
        raise Conversation.DoesNotExist

    existing_turn = ChatTurn.objects.filter(
        conversation=conversation,
        idempotency_key=idempotency_key,
    ).first()

    if existing_turn is None:
        return None

    if existing_turn.request_hash != request_hash:
        raise IdempotencyKeyReused()

    return ReplayedGeneration(chat_turn=existing_turn)
