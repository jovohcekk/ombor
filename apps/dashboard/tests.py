from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


class SeedDataCommandTests(TestCase):
    def test_seed_does_not_reset_existing_passwords_or_assign_demo_passwords(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Existing-Admin-Password-3827!",
        )
        output = StringIO()

        call_command("seed_data", stdout=output)

        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Existing-Admin-Password-3827!"))
        self.assertFalse(User.objects.get(username="manager").has_usable_password())
        self.assertFalse(User.objects.get(username="staff").has_usable_password())
        self.assertNotIn("Existing-Admin-Password-3827!", output.getvalue())
