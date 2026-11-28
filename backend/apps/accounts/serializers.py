from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

from rest_framework import serializers, status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    Throttled,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .login_throttle import (
    LoginProtectionUnavailable,
    clear_login_failures,
    get_login_cooldown,
    record_failed_login,
)

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializer for registering new user accounts."""

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
        style={"input_type": "password"},
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["id", "email", "password", "password_confirm"]

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        user = User(email=attrs["email"])

        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        try:
            return User.objects.create_user(
                password=password,
                **validated_data,
            )
        except IntegrityError:
            raise serializers.ValidationError(
                {"email": "A user with this email already exists."}
            )


class CurrentUserSerializer(serializers.ModelSerializer):
    """Serializer for the currently authenticated user's profile."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class LoginProtectionUnavailableAPIError(APIException):
    """Raised when login protection cannot access its cache backend."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Login is temporarily unavailable. Please try again later."
    default_code = "login_protection_unavailable"


class LoginSerializer(TokenObtainPairSerializer):
    """JWT login serializer with email/IP failure throttling."""

    def validate(self, attrs):
        request = self.context["request"]
        email = (attrs.get(self.username_field) or "").strip().lower()
        ip_address = request.META.get("REMOTE_ADDR") or "unknown"

        attrs[self.username_field] = email

        try:
            remaining = get_login_cooldown(email, ip_address)

            if remaining > 0:
                raise Throttled(wait=remaining)

            try:
                data = super().validate(attrs)
            except AuthenticationFailed:
                remaining = record_failed_login(email, ip_address)

                if remaining > 0:
                    raise Throttled(wait=remaining)

                raise

            clear_login_failures(email, ip_address)
            return data

        except LoginProtectionUnavailable as error:
            raise LoginProtectionUnavailableAPIError() from error
