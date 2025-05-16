from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist
from .models import User
from .serializers import NewUserSerializer, UserSerializer
from .authentication import APITokenAuthentication
from cryptomarket.permissions import IsAdmin

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = NewUserSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.create_user(
                name=serializer.validated_data["name"],
                password=None
            )
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class DeleteUserView(APIView):
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serialized_user = UserSerializer(user).data
            user.delete()
            return Response(serialized_user, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(
                {"detail": "User not found"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )