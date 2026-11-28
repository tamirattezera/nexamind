from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response

from apps.conversations.context.exceptions import (
    ContextChanged,
    ContextLimitExceeded,
    ContextUnavailable,
)
from apps.conversations.idempotency import (
    hash_message_content,
    parse_idempotency_key,
)
from apps.conversations.services import execution_service, orchestration
from apps.conversations.services.contracts import (
    AcceptedGeneration,
    ReplayedGeneration,
)
from apps.conversations.services.exceptions import (
    ChatTurnAlreadyInProgress,
    GenerationRateLimitExceeded,
    IdempotencyKeyReused,
)

from .models import ChatTurn, Conversation, Message
from .pagination import MessageCursorPagination
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)


class ConversationListCreateView(ListCreateAPIView):
    """List and create conversations for the authenticated user."""

    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete the authenticated user's conversation."""

    serializer_class = ConversationSerializer
    lookup_field = "id"

    def get_queryset(self):
        queryset = Conversation.objects.filter(user=self.request.user)

        if getattr(self, "_lock_conversation_for_update", False):
            queryset = queryset.select_for_update()

        return queryset

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            self._lock_conversation_for_update = True

            try:
                return super().update(request, *args, **kwargs)
            finally:
                self._lock_conversation_for_update = False

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            self._lock_conversation_for_update = True

            try:
                return super().destroy(request, *args, **kwargs)
            finally:
                self._lock_conversation_for_update = False


class MessageListView(ListAPIView):
    """List messages and submit generation requests for an owned conversation."""

    serializer_class = MessageSerializer
    pagination_class = MessageCursorPagination

    _FAILED_TURN_ERRORS = {
        "AI_PROVIDER_TIMEOUT": (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "The AI provider request timed out.",
        ),
        "CHAT_TURN_PROCESSING_TIMEOUT": (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Generation processing timed out.",
        ),
        "AI_PROVIDER_ERROR": (
            status.HTTP_502_BAD_GATEWAY,
            "The AI provider could not complete the request.",
        ),
        "INTERNAL_SERVER_ERROR": (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An internal error prevented generation from completing.",
        ),
    }

    @staticmethod
    def error_response(*, code, message, http_status, details=None):
        return Response(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                }
            },
            status=http_status,
        )

    def handle_exception(self, exc):
        # Keep existing GET exception behavior unchanged.
        if self.request.method == "POST" and isinstance(
            exc,
            (NotAuthenticated, AuthenticationFailed),
        ):
            return self.error_response(
                code="AUTHENTICATION_REQUIRED",
                message="Authentication is required to submit a message.",
                http_status=status.HTTP_401_UNAUTHORIZED,
            )

        return super().handle_exception(exc)

    def get_queryset(self):
        conversation = get_object_or_404(
            Conversation.objects.filter(user=self.request.user),
            id=self.kwargs["id"],
        )

        return Message.objects.filter(conversation=conversation)

    def _turn_error_response(self, chat_turn):
        http_status, default_message = self._FAILED_TURN_ERRORS.get(
            chat_turn.error_code,
            self._FAILED_TURN_ERRORS["INTERNAL_SERVER_ERROR"],
        )

        return self.error_response(
            code=(
                chat_turn.error_code
                if chat_turn.error_code in self._FAILED_TURN_ERRORS
                else "INTERNAL_SERVER_ERROR"
            ),
            message=chat_turn.error_message or default_message,
            http_status=http_status,
        )

    def _turn_response(self, chat_turn, *, replayed):
        if chat_turn.status == ChatTurn.Status.IN_PROGRESS:
            return Response(
                {
                    "status": "processing",
                    "message": (
                        "This request is still being processed. Retry the same "
                        "request with the same Idempotency-Key."
                    ),
                },
                status=status.HTTP_202_ACCEPTED,
            )

        if chat_turn.status == ChatTurn.Status.FAILED:
            return self._turn_error_response(chat_turn)

        if chat_turn.status != ChatTurn.Status.COMPLETED:
            return self.error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An internal error prevented generation from completing.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        assistant_message = chat_turn.assistant_message

        response_data = {
            "user_message": MessageSerializer(chat_turn.user_message).data,
            "assistant_message": {
                "id": str(assistant_message.id),
                "role": assistant_message.role,
                "content": assistant_message.content,
                "model": chat_turn.model_name,
                "usage": {
                    "input_tokens": chat_turn.input_tokens,
                    "output_tokens": chat_turn.output_tokens,
                    "total_tokens": chat_turn.total_tokens,
                },
                "created_at": assistant_message.created_at,
            },
        }

        return Response(
            response_data,
            status=(
                status.HTTP_200_OK
                if replayed
                else status.HTTP_201_CREATED
            ),
        )

    def post(self, request, *args, **kwargs):
        serializer = SendMessageSerializer(data=request.data)

        if not serializer.is_valid():
            return self.error_response(
                code="VALIDATION_ERROR",
                message="The submitted message is invalid.",
                http_status=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        raw_idempotency_key = request.headers.get("Idempotency-Key")

        if raw_idempotency_key is None:
            return self.error_response(
                code="IDEMPOTENCY_KEY_REQUIRED",
                message="The Idempotency-Key header is required.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            idempotency_key = parse_idempotency_key(raw_idempotency_key)
        except ValueError:
            return self.error_response(
                code="IDEMPOTENCY_KEY_INVALID",
                message="The Idempotency-Key header must contain a canonical UUID v4.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        content = serializer.validated_data["content"]
        conversation_id = self.kwargs["id"]

        current_user_message = Message(
            conversation_id=conversation_id,
            role=Message.Role.USER,
            content=content,
        )

        try:
            result = orchestration.prepare_and_accept_generation(
                user=request.user,
                conversation_id=conversation_id,
                current_user_message=current_user_message,
                idempotency_key=idempotency_key,
                request_hash=hash_message_content(content),
            )
        except Conversation.DoesNotExist:
            return self.error_response(
                code="RESOURCE_NOT_FOUND",
                message="The requested conversation was not found.",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        except IdempotencyKeyReused as exc:
            return self.error_response(
                code=exc.error_code,
                message=str(exc),
                http_status=status.HTTP_409_CONFLICT,
            )
        except ChatTurnAlreadyInProgress as exc:
            return self.error_response(
                code=exc.error_code,
                message=str(exc),
                http_status=status.HTTP_409_CONFLICT,
            )
        except ContextChanged as exc:
            return self.error_response(
                code=exc.error_code,
                message=str(exc),
                http_status=status.HTTP_409_CONFLICT,
            )
        except ContextLimitExceeded as exc:
            return self.error_response(
                code=exc.error_code,
                message=str(exc),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        except ContextUnavailable as exc:
            return self.error_response(
                code=exc.error_code,
                message=str(exc),
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except GenerationRateLimitExceeded as exc:
            return self.error_response(
                code=exc.error_code,
                message=str(exc),
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except ImproperlyConfigured:
            return self.error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An internal error prevented generation from completing.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if isinstance(result, AcceptedGeneration):
            chat_turn = execution_service.execute_generation(result)
            return self._turn_response(chat_turn, replayed=False)

        if isinstance(result, ReplayedGeneration):
            return self._turn_response(result.chat_turn, replayed=True)

        return self.error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An internal error prevented generation from completing.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
