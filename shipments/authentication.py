from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache
from shipments.models.user import User

TOKEN_PREFIX = 'auth_token:'

class TokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get("Authorization")
        if not token:
            return None
        user_id = cache.get(f"{TOKEN_PREFIX}{token}")
        if not user_id:
            raise AuthenticationFailed("Invalid or expired token")
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")
        return (user, None)
