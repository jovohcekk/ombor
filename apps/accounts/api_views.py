from django.contrib.auth import get_user_model
from rest_framework import viewsets

from apps.accounts.permissions import IsSuperAdmin
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin]
