from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.conversations.models import ChatTurn, Conversation


STALE_TURN_TIMEOUT = timedelta(seconds=120)
DEFAULT_BATCH_SIZE = 100

_TIMEOUT_ERROR_CODE = "CHAT_TURN_PROCESSING_TIMEOUT"
_TIMEOUT_ERROR_MESSAGE = "Generation processing timed out."


def _stale_candidate_ids(*, cutoff, batch_size):
    return list(
        ChatTurn.objects.filter(
            status=ChatTurn.Status.IN_PROGRESS,
        )
        .filter(
            Q(
                execution_claim_id__isnull=True,
                execution_claimed_at__isnull=True,
                started_at__lte=cutoff,
            )
            | Q(
                execution_claim_id__isnull=False,
                execution_claimed_at__isnull=False,
                execution_claimed_at__lte=cutoff,
            )
        )
        .annotate(
            eligibility_timestamp=Coalesce(
                "execution_claimed_at",
                "started_at",
            )
        )
        .order_by("eligibility_timestamp", "id")
        .values_list("id", flat=True)[:batch_size]
    )


def _recover_one_stale_turn(*, chat_turn_id, now):
    with transaction.atomic():
        conversation_id = (
            ChatTurn.objects.filter(pk=chat_turn_id)
            .values_list("conversation_id", flat=True)
            .first()
        )

        if conversation_id is None:
            return False

        Conversation.objects.select_for_update().get(pk=conversation_id)

        chat_turn = ChatTurn.objects.select_for_update().get(
            pk=chat_turn_id,
        )

        if (
            chat_turn.conversation_id != conversation_id
            or chat_turn.status != ChatTurn.Status.IN_PROGRESS
        ):
            return False

        eligibility_timestamp = (
            chat_turn.execution_claimed_at
            if chat_turn.execution_claim_id is not None
            else chat_turn.started_at
        )

        if eligibility_timestamp is None:
            return False

        if eligibility_timestamp > now - STALE_TURN_TIMEOUT:
            return False

        chat_turn.status = ChatTurn.Status.FAILED
        chat_turn.error_code = _TIMEOUT_ERROR_CODE
        chat_turn.error_message = _TIMEOUT_ERROR_MESSAGE
        chat_turn.completed_at = now
        chat_turn.execution_claim_id = None
        chat_turn.execution_claimed_at = None

        chat_turn.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "completed_at",
                "execution_claim_id",
                "execution_claimed_at",
            ]
        )

        return True


def recover_stale_turns(*, batch_size=DEFAULT_BATCH_SIZE):
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer.")

    now = timezone.now()
    cutoff = now - STALE_TURN_TIMEOUT

    candidate_ids = _stale_candidate_ids(
        cutoff=cutoff,
        batch_size=batch_size,
    )

    recovered_count = 0

    for chat_turn_id in candidate_ids:
        if _recover_one_stale_turn(
            chat_turn_id=chat_turn_id,
            now=timezone.now(),
        ):
            recovered_count += 1

    return recovered_count
