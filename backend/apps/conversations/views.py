from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from .models import Conversation
from .serializers import ConversationSerializer


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
