from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from shipments.models.user import User
import uuid
import secrets
from django.core.cache import cache

TOKEN_PREFIX = 'auth_token:'
TOKEN_EXPIRY = 60 * 60 * 24  # 24 hours

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"detail": "Missing username or password"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        user = User(username=username)
        user.set_password(password)
        user.save()
        return Response({"user_id": str(user.user_id)}, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.check_password(password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        token = secrets.token_hex(32)
        cache.set(f"{TOKEN_PREFIX}{token}", str(user.user_id), TOKEN_EXPIRY)
        return Response({"user_id": str(user.user_id), "token": token}, status=status.HTTP_200_OK)

