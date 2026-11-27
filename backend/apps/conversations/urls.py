from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    MessageListView,
)

urlpatterns = [
    path(
        "",
        ConversationListCreateView.as_view(),
        name="conversation-list-create",
    ),
    path(
        "<uuid:id>/messages/",
        MessageListView.as_view(),
        name="message-list",
    ),
    path(
        "<uuid:id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
]
