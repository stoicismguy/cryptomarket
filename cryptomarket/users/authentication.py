from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User
from django.shortcuts import get_object_or_404

class APITokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        try:
            token_type, api_key = auth_header.split()
            if token_type != "TOKEN":
                raise AuthenticationFailed("Invalid token type. Expected 'TOKEN'")
            user = get_object_or_404(User, api_key=api_key, is_active=True)
            return (user, None)
        except (ValueError, User.DoesNotExist):
            raise AuthenticationFailed("Invalid or missing API key")