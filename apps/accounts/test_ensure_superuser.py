import os
import re
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import UserRole

User = get_user_model()
COMMAND = "ensure_superuser"
PASSWORD = "BootstrapPass!4821"
ENV = {
    "DJANGO_SUPERUSER_USERNAME": "deploy-admin",
    "DJANGO_SUPERUSER_EMAIL": "deploy-admin@example.com",
    "DJANGO_SUPERUSER_PASSWORD": PASSWORD,
    "ADMIN_USERNAME": "",
    "ADMIN_EMAIL": "",
    "ADMIN_PASSWORD": "",
}


def run_command(env=None, **options):
    stdout = StringIO()
    with patch.dict(os.environ, env if env is not None else ENV):
        call_command(COMMAND, stdout=stdout, **options)
    return stdout.getvalue()


class EnsureSuperuserCommandTests(TestCase):
    def test_creates_superuser_from_environment(self):
        run_command()

        user = User.objects.get(username="deploy-admin")
        self.assertEqual(user.email, "deploy-admin@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, UserRole.SUPER_ADMIN)
        self.assertTrue(user.check_password(PASSWORD))

    def test_is_idempotent(self):
        run_command()
        output = run_command()

        self.assertEqual(
            User.objects.filter(username__iexact="deploy-admin").count(), 1
        )
        self.assertIn("already up to date", output)

    def test_repairs_existing_user_and_syncs_password(self):
        User.objects.create_user(
            username="deploy-admin",
            password="OldPassword!4821",
        )

        run_command()

        user = User.objects.get(username="deploy-admin")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, UserRole.SUPER_ADMIN)
        self.assertTrue(user.check_password(PASSWORD))

    def test_generates_and_reports_password_when_not_configured(self):
        env = dict(ENV, DJANGO_SUPERUSER_PASSWORD="")

        output = run_command(env)

        user = User.objects.get(username="deploy-admin")
        match = re.search(r"generated.*?:\n\s+(\S+)", output)
        self.assertIsNotNone(match)
        self.assertTrue(user.check_password(match.group(1)))

    def test_keeps_existing_password_when_not_configured(self):
        existing = User.objects.create_superuser(
            username="deploy-admin",
            email="deploy-admin@example.com",
            password="KeepThisPass!4821",
        )
        env = dict(ENV, DJANGO_SUPERUSER_PASSWORD="")

        run_command(env)

        existing.refresh_from_db()
        self.assertTrue(existing.check_password("KeepThisPass!4821"))
