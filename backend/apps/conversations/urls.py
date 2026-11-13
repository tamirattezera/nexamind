from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
)

urlpatterns = [
    path(
        "",
        ConversationListCreateView.as_view(),
        name="conversation-list-create",
    ),
    path(
        "<uuid:id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
]
