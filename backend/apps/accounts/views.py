from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import CurrentUserSerializer, RegistrationSerializer


class RegistrationView(CreateAPIView):
    """API endpoint for registering new user accounts."""

    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer


class CurrentUserView(RetrieveAPIView):
    """API endpoint for retrieving the authenticated user's profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserSerializer

    def get_object(self):
        return self.request.user
