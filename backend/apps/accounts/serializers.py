from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

from rest_framework import serializers

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
