from rest_framework import serializers
from .models import User, UserRole

class NewUserSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=3, max_length=255)

class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=UserRole.choices)

    class Meta:
        model = User
        fields = ["id", "name", "role", "api_key"]
        read_only_fields = ["id", "api_key"]