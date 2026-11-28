from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.conversations.context.exceptions import ContextSnapshotStale
from apps.conversations.context.freshness import is_context_snapshot_fresh
from apps.conversations.context.history import get_eligible_history_messages
from apps.conversations.idempotency import hash_message_content
from apps.conversations.instructions.platform import (
    PLATFORM_INSTRUCTION_VERSION,
    PLATFORM_SYSTEM_INSTRUCTION,
)
from apps.conversations.models import (
    ChatTurn,
    Conversation,
    GenerationSubmission,
    Message,
)
from apps.conversations.services.contracts import (
    AcceptedGeneration,
    ReplayedGeneration,
)
from apps.conversations.services.exceptions import (
    ChatTurnAlreadyInProgress,
    GenerationRateLimitExceeded,
    IdempotencyKeyReused,
)
from apps.conversations.services.generation_config import (
    get_generation_rate_limit_config,
)
from apps.ai.config import GeminiConfig


@transaction.atomic
def accept_generation(
    *,
    user,
    conversation_id,
    current_user_message,
    idempotency_key,
    request_hash,
    prepared_context,
    generation_config: GeminiConfig,
):
    """
    Atomically accept a new generation or return an idempotent replay.

    Context preparation and provider token counting must happen before
    this function is called.
    """
    if not current_user_message._state.adding:
        raise ValueError("The current user message must be unsaved.")

    if current_user_message.role != Message.Role.USER:
        raise ValueError("The current message must have the user role.")

    if current_user_message.conversation_id != conversation_id:
        raise ValueError("The current message belongs to another conversation.")

    if hash_message_content(current_user_message.content) != request_hash:
        raise ValueError("The request hash does not match the message content.")

    # Lock order begins with Conversation.
    conversation = Conversation.objects.select_for_update().get(pk=conversation_id)

    # Do not reveal whether another user's conversation exists.
    if conversation.user_id != user.pk:
        raise Conversation.DoesNotExist

    # Idempotency takes precedence over active-turn and freshness checks.
    existing_turn = ChatTurn.objects.filter(
        conversation=conversation,
        idempotency_key=idempotency_key,
    ).first()

    if existing_turn is not None:
        if existing_turn.request_hash != request_hash:
            raise IdempotencyKeyReused()

        return ReplayedGeneration(chat_turn=existing_turn)

    # A different request cannot start while another turn is active.
    active_turn_exists = ChatTurn.objects.filter(
        conversation=conversation,
        status=ChatTurn.Status.IN_PROGRESS,
    ).exists()

    if active_turn_exists:
        raise ChatTurnAlreadyInProgress()

    # Revalidate the snapshot while Conversation is locked.
    eligible_history = get_eligible_history_messages(
        conversation,
        current_user_message,
    )

    context_is_fresh = is_context_snapshot_fresh(
        prepared_context=prepared_context,
        current_user_message=current_user_message,
        platform_instruction_version=PLATFORM_INSTRUCTION_VERSION,
        platform_instruction=PLATFORM_SYSTEM_INSTRUCTION,
        custom_instruction=conversation.custom_instructions,
        eligible_history_message_ids=tuple(message.id for message in eligible_history),
    )

    if not context_is_fresh:
        raise ContextSnapshotStale()

    # Lock order continues with User.
    User = get_user_model()
    locked_user = User.objects.select_for_update().get(pk=user.pk)

    config = get_generation_rate_limit_config()
    window_start = timezone.now() - timedelta(seconds=config.window_seconds)

    recent_submission_count = GenerationSubmission.objects.filter(
        user=locked_user,
        created_at__gte=window_start,
    ).count()

    if recent_submission_count >= config.limit:
        raise GenerationRateLimitExceeded()

    generation_metadata = {
        "schema_version": 1,
        "provider": "gemini",
        "requested_model": generation_config.model,
        "thinking_level": generation_config.thinking_level,
    }

    # All writes below belong to the same transaction.
    GenerationSubmission.objects.create(user=locked_user)

    current_user_message.save(force_insert=True)

    chat_turn = ChatTurn.objects.create(
        conversation=conversation,
        user_message=current_user_message,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        generation_metadata=generation_metadata,
        max_output_tokens=generation_config.max_output_tokens,
        system_instruction_version=(prepared_context.platform_instruction_version),
        system_instruction_snapshot=(prepared_context.platform_instruction_snapshot),
        custom_instruction_snapshot=(prepared_context.custom_instruction_snapshot),
        selected_history_message_ids=[
            str(message_id)
            for message_id in prepared_context.selected_history_message_ids
        ],
    )

    return AcceptedGeneration(chat_turn=chat_turn)
