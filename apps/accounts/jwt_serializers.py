from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        raw = attrs.get(self.username_field)
        user = User.objects.filter(username__iexact=raw).first()
        if user is None and raw:
            matches = User.objects.filter(Q(email__iexact=raw) & ~Q(email=""))
            if matches.count() == 1:
                user = matches.first()
        if user is not None:
            attrs[self.username_field] = user.get_username()
        return super().validate(attrs)
