import uuid

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from apps.ai.providers.gemini import (
    ProviderError,
    ProviderTimeoutError,
)
from apps.ai.services import generate_response
from apps.conversations.models import ChatTurn, Conversation, Message

from .contracts import AcceptedGeneration
from .execution import prepare_generation_execution


_PROVIDER_TIMEOUT_CODE = "AI_PROVIDER_TIMEOUT"
_PROVIDER_ERROR_CODE = "AI_PROVIDER_ERROR"
_INTERNAL_ERROR_CODE = "INTERNAL_SERVER_ERROR"

_PROVIDER_TIMEOUT_MESSAGE = "The AI provider request timed out."
_PROVIDER_ERROR_MESSAGE = "The AI provider could not complete the request."
_INTERNAL_ERROR_MESSAGE = (
    "An internal error prevented generation from completing."
)


def _lock_chat_turn(*, chat_turn_id, conversation_id):
    """
    Lock Conversation first, then ChatTurn.

    This preserves the lock order used by the acceptance service.
    The caller must already be inside transaction.atomic().
    """
    Conversation.objects.select_for_update().get(pk=conversation_id)

    chat_turn = ChatTurn.objects.select_for_update().get(
        pk=chat_turn_id,
    )

    if chat_turn.conversation_id != conversation_id:
        raise ValueError("ChatTurn conversation does not match its accepted reference.")

    return chat_turn



def _acquire_execution_claim(*, chat_turn_id, conversation_id):
    """Atomically acquire execution ownership for one in-progress turn."""
    with transaction.atomic():
        chat_turn = _lock_chat_turn(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
        )

        if chat_turn.status != ChatTurn.Status.IN_PROGRESS:
            raise ValueError(
                "Only an in-progress ChatTurn can be executed."
            )

        if chat_turn.execution_claim_id is not None:
            return chat_turn, None

        claim_id = uuid.uuid4()
        claimed_at = timezone.now()

        chat_turn.execution_claim_id = claim_id
        chat_turn.execution_claimed_at = claimed_at
        chat_turn.save(
            update_fields=[
                "execution_claim_id",
                "execution_claimed_at",
            ]
        )

    return chat_turn, claim_id


def _persist_failure(
    *,
    chat_turn_id,
    conversation_id,
    claim_id,
    error_code,
    error_message,
):
    """Persist failure only while this worker still owns the execution claim."""
    with transaction.atomic():
        chat_turn = _lock_chat_turn(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
        )

        if (
            chat_turn.status != ChatTurn.Status.IN_PROGRESS
            or chat_turn.execution_claim_id != claim_id
        ):
            return chat_turn

        chat_turn.status = ChatTurn.Status.FAILED
        chat_turn.error_code = error_code
        chat_turn.error_message = error_message
        chat_turn.completed_at = timezone.now()
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

    return chat_turn


def _persist_success(
    *,
    chat_turn_id,
    conversation_id,
    claim_id,
    generation_result,
):
    """Persist success only while this worker still owns the execution claim."""
    with transaction.atomic():
        chat_turn = _lock_chat_turn(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
        )

        if (
            chat_turn.status != ChatTurn.Status.IN_PROGRESS
            or chat_turn.execution_claim_id != claim_id
        ):
            return chat_turn

        assistant_message = Message.objects.create(
            conversation_id=conversation_id,
            role=Message.Role.ASSISTANT,
            content=generation_result.text,
        )

        chat_turn.assistant_message = assistant_message
        chat_turn.model_name = generation_result.model_name
        chat_turn.input_tokens = generation_result.input_tokens
        chat_turn.output_tokens = generation_result.output_tokens
        chat_turn.total_tokens = generation_result.total_tokens
        chat_turn.status = ChatTurn.Status.COMPLETED
        chat_turn.completed_at = timezone.now()

        chat_turn.error_code = None
        chat_turn.error_message = None
        chat_turn.execution_claim_id = None
        chat_turn.execution_claimed_at = None

        chat_turn.save(
            update_fields=[
                "assistant_message",
                "model_name",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "status",
                "completed_at",
                "error_code",
                "error_message",
                "execution_claim_id",
                "execution_claimed_at",
            ]
        )

    return chat_turn


def execute_generation(accepted: AcceptedGeneration) -> ChatTurn:
    """
    Execute one newly accepted generation synchronously.

    Provider execution happens outside database transactions.
    Persistence uses short transactions with a consistent lock order.
    """
    if not isinstance(accepted, AcceptedGeneration):
        raise TypeError(
            "execute_generation requires an AcceptedGeneration."
        )

    chat_turn_id = accepted.chat_turn.pk
    conversation_id = accepted.chat_turn.conversation_id

    # Acquire persistent execution ownership before preparation or provider work.
    chat_turn, claim_id = _acquire_execution_claim(
        chat_turn_id=chat_turn_id,
        conversation_id=conversation_id,
    )

    # Another worker already owns this turn. Do not call the provider again.
    if claim_id is None:
        return chat_turn

    # Only preparation and provider execution are inside this try block.
    # No database transaction or row lock is held during the provider call.
    try:
        execution_input = prepare_generation_execution(chat_turn)

        generation_result = generate_response(
            execution_input.request,
            config=execution_input.config,
        )

    except ProviderTimeoutError:
        return _persist_failure(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
            claim_id=claim_id,
            error_code=_PROVIDER_TIMEOUT_CODE,
            error_message=_PROVIDER_TIMEOUT_MESSAGE,
        )

    except ProviderError:
        return _persist_failure(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
            claim_id=claim_id,
            error_code=_PROVIDER_ERROR_CODE,
            error_message=_PROVIDER_ERROR_MESSAGE,
        )

    except ImproperlyConfigured:
        return _persist_failure(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
            claim_id=claim_id,
            error_code=_INTERNAL_ERROR_CODE,
            error_message=_INTERNAL_ERROR_MESSAGE,
        )

    except Exception:
        return _persist_failure(
            chat_turn_id=chat_turn_id,
            conversation_id=conversation_id,
            claim_id=claim_id,
            error_code=_INTERNAL_ERROR_CODE,
            error_message=_INTERNAL_ERROR_MESSAGE,
        )

    # Deliberately outside the exception handler:
    # database persistence errors must propagate, not become provider failures.
    return _persist_success(
        chat_turn_id=chat_turn_id,
        conversation_id=conversation_id,
        claim_id=claim_id,
        generation_result=generation_result,
    )
