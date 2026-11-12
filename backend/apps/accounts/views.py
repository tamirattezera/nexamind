from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from .serializers import RegistrationSerializer


class RegistrationView(CreateAPIView):
    """API endpoint for registering new user accounts."""

    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer
