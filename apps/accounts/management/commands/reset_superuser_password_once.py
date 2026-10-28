import os

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Temporarily reset one existing superuser password from environment variables"

    def handle(self, *args, **options):
        username = os.environ.get("OMBOR_RESET_SUPERUSER_USERNAME")
        password = os.environ.get("OMBOR_RESET_SUPERUSER_PASSWORD")
        confirmation = os.environ.get("OMBOR_RESET_SUPERUSER_CONFIRM_PRODUCTION")
        expected_host = os.environ.get("OMBOR_RESET_SUPERUSER_EXPECTED_DB_HOST")
        expected_name = os.environ.get("OMBOR_RESET_SUPERUSER_EXPECTED_DB_NAME")

        if not username:
            raise CommandError("OMBOR_RESET_SUPERUSER_USERNAME must be set.")
        if not password:
            raise CommandError("OMBOR_RESET_SUPERUSER_PASSWORD must be set.")
        if confirmation != "I_UNDERSTAND_THIS_CHANGES_A_PRODUCTION_PASSWORD":
            raise CommandError(
                "Set OMBOR_RESET_SUPERUSER_CONFIRM_PRODUCTION to the required "
                "confirmation value before running this command."
            )
        if connection.vendor != "postgresql":
            raise CommandError("Refusing to reset a password unless the database is PostgreSQL.")

        actual_host = connection.settings_dict["HOST"]
        actual_name = connection.settings_dict["NAME"]
        if not expected_host or actual_host.casefold() != expected_host.casefold():
            raise CommandError("The configured database host does not match the expected host.")
        if not expected_name or actual_name != expected_name:
            raise CommandError("The configured database name does not match the expected name.")

        user_model = get_user_model()
        try:
            with transaction.atomic():
                user = user_model._default_manager.select_for_update().get(username=username)
                if not user.is_superuser:
                    raise CommandError("The selected account is not a superuser.")

                try:
                    password_validation.validate_password(password, user=user)
                except ValidationError as exc:
                    raise CommandError("; ".join(exc.messages)) from exc

                user.set_password(password)
                user.save(update_fields=["password"])
                user.refresh_from_db(fields=["password"])
                if not user.check_password(password):
                    raise CommandError("Password verification failed; the change was rolled back.")
        except user_model.DoesNotExist as exc:
            raise CommandError("No account with that username exists.") from exc

        self.stdout.write(
            self.style.SUCCESS(f"Password reset and verified for superuser {username!r}.")
        )
