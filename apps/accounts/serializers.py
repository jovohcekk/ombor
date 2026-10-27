from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "password",
            "date_joined",
        ]
        read_only_fields = ["date_joined"]

    def validate_username(self, value):
        users = User.objects.filter(username__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError(_("This username is already registered."))
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if value:
            users = User.objects.filter(email__iexact=value)
            if self.instance:
                users = users.exclude(pk=self.instance.pk)
            if users.exists():
                raise serializers.ValidationError(_("This email address is already registered."))
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
