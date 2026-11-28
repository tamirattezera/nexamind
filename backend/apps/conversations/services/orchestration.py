from apps.ai.config import get_gemini_config
from apps.conversations.context.builder import (
    prepare_conversation_context,
)
from apps.conversations.context.exceptions import (
    ContextChanged,
    ContextLimitExceeded,
    ContextSnapshotStale,
    ContextUnavailable,
)
from apps.conversations.models import Conversation
from apps.conversations.services.acceptance import accept_generation
from apps.conversations.services.replay import find_idempotent_replay


MAX_CONTEXT_PREPARATION_ATTEMPTS = 3


def prepare_and_accept_generation(
    *,
    user,
    conversation_id,
    current_user_message,
    idempotency_key,
    request_hash,
):
    """
    Resolve replays before context preparation, then prepare and accept
    a new generation with bounded context freshness retries.
    """
    replay = find_idempotent_replay(
        user=user,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    if replay is not None:
        return replay

    # Capture one configuration for context preparation and generation.
    generation_config = get_gemini_config()

    for attempt in range(MAX_CONTEXT_PREPARATION_ATTEMPTS):
        conversation = Conversation.objects.get(
            pk=conversation_id,
            user=user,
        )

        try:
            prepared_context = prepare_conversation_context(
                conversation=conversation,
                current_user_message=current_user_message,
                generation_config=generation_config,
            )
        except (ContextLimitExceeded, ContextUnavailable):
            # Another request may have accepted this idempotency key
            # while context preparation was running.
            replay = find_idempotent_replay(
                user=user,
                conversation_id=conversation_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )

            if replay is not None:
                return replay

            raise

        try:
            return accept_generation(
                user=user,
                conversation_id=conversation_id,
                current_user_message=current_user_message,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                prepared_context=prepared_context,
                generation_config=generation_config,
            )
        except ContextSnapshotStale as exc:
            if attempt == MAX_CONTEXT_PREPARATION_ATTEMPTS - 1:
                raise ContextChanged() from exc

    raise AssertionError("Unreachable generation orchestration state.")
