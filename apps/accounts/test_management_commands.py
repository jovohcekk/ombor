import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

User = get_user_model()
COMMAND = "reset_superuser_password_once"
NEW_PASSWORD = "NewSafePass!4821"
COMMAND_ENV = {
    "OMBOR_RESET_SUPERUSER_USERNAME": "target-admin",
    "OMBOR_RESET_SUPERUSER_PASSWORD": NEW_PASSWORD,
    "OMBOR_RESET_SUPERUSER_CONFIRM_PRODUCTION": (
        "I_UNDERSTAND_THIS_CHANGES_A_PRODUCTION_PASSWORD"
    ),
    "OMBOR_RESET_SUPERUSER_EXPECTED_DB_HOST": "production.example",
    "OMBOR_RESET_SUPERUSER_EXPECTED_DB_NAME": "ombor",
}


class ResetSuperuserPasswordCommandTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="target-admin",
            email="admin@example.com",
            password="PreviousSafePass!4821",
        )

    def run_command_on_expected_database(self, stdout=None):
        with (
            patch.dict(os.environ, COMMAND_ENV),
            patch("apps.accounts.management.commands.reset_superuser_password_once.connection") as db,
        ):
            db.vendor = "postgresql"
            db.settings_dict = {"HOST": "production.example", "NAME": "ombor"}
            call_command(COMMAND, stdout=stdout or StringIO())

    def test_resets_only_the_selected_superuser_and_verifies_without_printing_password(self):
        output = StringIO()

        self.run_command_on_expected_database(stdout=output)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(NEW_PASSWORD))
        self.assertNotIn(NEW_PASSWORD, output.getvalue())
        self.assertIn("Password reset and verified", output.getvalue())

    def test_refuses_to_change_a_non_superuser(self):
        self.admin.is_superuser = False
        self.admin.save(update_fields=["is_superuser"])

        with self.assertRaisesMessage(CommandError, "not a superuser"):
            self.run_command_on_expected_database()

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("PreviousSafePass!4821"))

    def test_refuses_non_postgresql_database(self):
        with patch.dict(os.environ, COMMAND_ENV), self.assertRaisesMessage(
            CommandError, "unless the database is PostgreSQL"
        ):
            call_command(COMMAND, stdout=StringIO())

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("PreviousSafePass!4821"))

    def test_refuses_mismatched_database_host(self):
        variables = dict(COMMAND_ENV, OMBOR_RESET_SUPERUSER_EXPECTED_DB_HOST="wrong.example")

        with (
            patch.dict(os.environ, variables),
            patch("apps.accounts.management.commands.reset_superuser_password_once.connection") as db,
            self.assertRaisesMessage(CommandError, "host does not match"),
        ):
            db.vendor = "postgresql"
            db.settings_dict = {"HOST": "production.example", "NAME": "ombor"}
            call_command(COMMAND, stdout=StringIO())

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("PreviousSafePass!4821"))

    def test_refuses_mismatched_database_name(self):
        variables = dict(COMMAND_ENV, OMBOR_RESET_SUPERUSER_EXPECTED_DB_NAME="staging")

        with (
            patch.dict(os.environ, variables),
            patch("apps.accounts.management.commands.reset_superuser_password_once.connection") as db,
            self.assertRaisesMessage(CommandError, "database name does not match"),
        ):
            db.vendor = "postgresql"
            db.settings_dict = {"HOST": "production.example", "NAME": "ombor"}
            call_command(COMMAND, stdout=StringIO())

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("PreviousSafePass!4821"))
