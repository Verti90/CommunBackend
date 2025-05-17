from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    print("🔐 Attempting login for:", username)

    user = authenticate(username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        print("✅ Login successful:", user.username)
        return Response({
            "token": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            },
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": "staff" if user.is_staff else "resident"
            }
        }, status=status.HTTP_200_OK)
    else:
        print("❌ Login failed for:", username)
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)