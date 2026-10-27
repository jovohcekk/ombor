from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super Admin")
    MANAGER = "manager", _("Manager")
    STAFF = "staff", _("Staff")


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STAFF,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["username"]
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_ci_uniq",
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=~Q(email=""),
                name="accounts_user_email_ci_uniq",
            ),
        ]

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role in (UserRole.MANAGER, UserRole.SUPER_ADMIN) or self.is_superuser

    @property
    def can_manage_users(self):
        return self.is_super_admin

    @property
    def can_manage_products(self):
        return self.is_manager

    @property
    def can_manage_stock(self):
        return self.is_manager or self.role == UserRole.STAFF

    @property
    def can_view_reports(self):
        return self.is_manager
