from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            matches = User.objects.filter(Q(email__iexact=username) & ~Q(email=""))
            if matches.count() == 1:
                user = matches.first()
        if user is None:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
