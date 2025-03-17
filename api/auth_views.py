from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    """User registration endpoint"""
    username = request.data.get("username")
    password = request.data.get("password")

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already taken"}, status=400)

    user = User.objects.create_user(username=username, password=password)
    refresh = RefreshToken.for_user(user)
    return Response({"refresh": str(refresh), "access": str(refresh.access_token)})

@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    """User login endpoint"""
    username = request.data.get("username")
    password = request.data.get("password")

    try:
        user = User.objects.get(username=username)
        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=400)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=400)

    refresh = RefreshToken.for_user(user)
    return Response({"refresh": str(refresh), "access": str(refresh.access_token)})
