import uuid

from django.core import signing
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import BasePagination
from rest_framework.response import Response


CURSOR_SALT = "conversations.message-pagination.v1"
CURSOR_MAX_AGE = 60 * 60 * 24
CURSOR_VERSION = 1


class InvalidMessageCursor(Exception):
    """Raised when a message pagination cursor is invalid."""


def encode_message_cursor(conversation_id, message):
    """
    Create a signed cursor bound to a conversation and message boundary.
    """
    payload = {
        "version": CURSOR_VERSION,
        "conversation_id": str(conversation_id),
        "created_at": message.created_at.isoformat(),
        "message_id": str(message.id),
    }

    return signing.dumps(payload, salt=CURSOR_SALT)


def decode_message_cursor(token, conversation_id):
    """
    Validate a signed cursor and return its timestamp and message UUID.
    """
    try:
        payload = signing.loads(
            token,
            salt=CURSOR_SALT,
            max_age=CURSOR_MAX_AGE,
        )

        if not isinstance(payload, dict):
            raise InvalidMessageCursor

        if payload.get("version") != CURSOR_VERSION:
            raise InvalidMessageCursor

        if payload.get("conversation_id") != str(conversation_id):
            raise InvalidMessageCursor

        timestamp = payload.get("created_at")
        message_id = payload.get("message_id")

        if not isinstance(timestamp, str) or not isinstance(message_id, str):
            raise InvalidMessageCursor

        parsed_timestamp = parse_datetime(timestamp)
        parsed_message_id = uuid.UUID(message_id)

        if parsed_timestamp is None or parsed_timestamp.utcoffset() is None:
            raise InvalidMessageCursor

        if str(parsed_message_id) != message_id:
            raise InvalidMessageCursor

        return parsed_timestamp, parsed_message_id

    except (
        signing.BadSignature,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise InvalidMessageCursor from exc


class MessageCursorPagination(BasePagination):
    """
    Cursor pagination for conversation messages.

    Retrieves newest pages first while returning each page in
    chronological order.
    """

    page_size = 30
    max_page_size = 100
    page_size_query_param = "page_size"
    cursor_query_param = "cursor"

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.page = []
        self.has_more = False
        self.next_cursor = None

        page_size = self._get_page_size(request)
        conversation_id = self._get_conversation_id(view)

        cursor_token = request.query_params.get(self.cursor_query_param)

        if cursor_token is not None:
            try:
                cursor_created_at, cursor_message_id = decode_message_cursor(
                    cursor_token,
                    conversation_id,
                )
            except InvalidMessageCursor as exc:
                raise ValidationError({
                    "cursor": "Invalid or expired pagination cursor."
                }) from exc

            queryset = queryset.filter(
                Q(created_at__lt=cursor_created_at)
                | Q(
                    created_at=cursor_created_at,
                    id__lt=cursor_message_id,
                )
            )

        records = list(
            queryset.order_by("-created_at", "-id")[: page_size + 1]
        )

        self.has_more = len(records) > page_size

        selected_records = records[:page_size]
        selected_records.reverse()
        self.page = selected_records

        if self.has_more and self.page:
            self.next_cursor = encode_message_cursor(
                conversation_id,
                self.page[0],
            )

        return self.page

    def get_paginated_response(self, data):
        return Response({
            "results": data,
            "next": self.next_cursor,
            "has_more": self.has_more,
        })

    def _get_page_size(self, request):
        raw_page_size = request.query_params.get(
            self.page_size_query_param
        )

        if raw_page_size is None:
            return self.page_size

        if not raw_page_size.isascii() or not raw_page_size.isdecimal():
            raise ValidationError({
                "page_size": "Must be a positive decimal integer."
            })

        page_size = int(raw_page_size)

        if not 1 <= page_size <= self.max_page_size:
            raise ValidationError({
                "page_size": (
                    f"Must be between 1 and {self.max_page_size}."
                )
            })

        return page_size

    def _get_conversation_id(self, view):
        if view is None:
            raise ValueError(
                "MessageCursorPagination requires a view "
                "with a conversation URL parameter."
            )

        conversation_id = (
            view.kwargs.get("id")
            or view.kwargs.get("conversation_id")
        )

        if conversation_id is None:
            raise ValueError(
                "Conversation ID is missing from the URL parameters."
            )

        return conversation_id
