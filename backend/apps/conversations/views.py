from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .models import Conversation, Message
from .pagination import MessageCursorPagination
from .serializers import ConversationSerializer, MessageSerializer


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
        return Conversation.objects.filter(user=self.request.user)



class MessageListView(ListAPIView):
    """List messages from a conversation owned by the authenticated user."""

    serializer_class = MessageSerializer
    pagination_class = MessageCursorPagination

    def get_queryset(self):
        conversation = get_object_or_404(
            Conversation.objects.filter(user=self.request.user),
            id=self.kwargs["id"],
        )

        return Message.objects.filter(conversation=conversation)
