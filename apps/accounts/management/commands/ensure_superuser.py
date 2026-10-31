import os

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.crypto import get_random_string

from apps.accounts.models import UserRole

User = get_user_model()

USERNAME_ENV = ("DJANGO_SUPERUSER_USERNAME", "ADMIN_USERNAME")
EMAIL_ENV = ("DJANGO_SUPERUSER_EMAIL", "ADMIN_EMAIL")
PASSWORD_ENV = ("DJANGO_SUPERUSER_PASSWORD", "ADMIN_PASSWORD")


def _first_env(names):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


class Command(BaseCommand):
    help = (
        "Create or repair the admin superuser from DJANGO_SUPERUSER_* "
        "environment variables. Safe to run on every deploy."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=_first_env(USERNAME_ENV) or "admin",
            help="Superuser username (default: DJANGO_SUPERUSER_USERNAME or admin).",
        )
        parser.add_argument(
            "--email",
            default=_first_env(EMAIL_ENV),
            help="Superuser email (default: DJANGO_SUPERUSER_EMAIL).",
        )
        parser.add_argument(
            "--password",
            default=_first_env(PASSWORD_ENV),
            help="Superuser password (default: DJANGO_SUPERUSER_PASSWORD).",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        user = User.objects.filter(username__iexact=username).first()

        if user is None:
            generated = not password
            if generated:
                password = get_random_string(24)
            self._validate(password)

            with transaction.atomic():
                user = User.objects.create_superuser(
                    username=username,
                    email=self._available_email(email),
                    password=password,
                    role=UserRole.SUPER_ADMIN,
                )

            self.stdout.write(
                self.style.SUCCESS(f"Created superuser {user.get_username()!r}.")
            )
            if generated:
                self.stdout.write(
                    self.style.WARNING(
                        "DJANGO_SUPERUSER_PASSWORD is not set, so a random password was "
                        f"generated. Sign in as {user.get_username()!r} with:\n"
                        f"    {password}\n"
                        "Set DJANGO_SUPERUSER_PASSWORD in the hosting environment to "
                        "control it on future deploys."
                    )
                )
            else:
                self.stdout.write(
                    "Sign in with the password from DJANGO_SUPERUSER_PASSWORD."
                )
            return

        changes = []
        if not user.is_superuser:
            user.is_superuser = True
            changes.append("is_superuser")
        if not user.is_staff:
            user.is_staff = True
            changes.append("is_staff")
        if not user.is_active:
            user.is_active = True
            changes.append("is_active")
        if user.role != UserRole.SUPER_ADMIN:
            user.role = UserRole.SUPER_ADMIN
            changes.append("role")

        available_email = self._available_email(email, exclude_pk=user.pk)
        if available_email and user.email != available_email:
            user.email = available_email
            changes.append("email")

        if password and not user.check_password(password):
            self._validate(password, user=user)
            user.set_password(password)
            changes.append("password")

        if changes:
            user.save(update_fields=changes)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated superuser {user.get_username()!r}: {', '.join(changes)}."
                )
            )
        else:
            self.stdout.write(
                f"Superuser {user.get_username()!r} is already up to date."
            )

    def _validate(self, password, user=None):
        try:
            password_validation.validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc

    def _available_email(self, email, exclude_pk=None):
        if not email:
            return ""
        conflicts = User.objects.filter(email__iexact=email)
        if exclude_pk is not None:
            conflicts = conflicts.exclude(pk=exclude_pk)
        if conflicts.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Email {email!r} is already used by another account; "
                    "leaving the admin email unchanged."
                )
            )
            return ""
        return email
