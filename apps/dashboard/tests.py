from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserRole
from apps.products.models import Category

User = get_user_model()


class DashboardRenderingTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="dashboard-manager",
            password="SecureDashboardPass!4821",
            role=UserRole.MANAGER,
        )
        self.client.force_login(self.manager)

    def test_dashboard_chart_json_escapes_script_markup_in_category_names(self):
        Category.objects.create(name="</script><script>alert(1)</script>")

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, r"\u003C/script\u003E")
        self.assertNotContains(response, "</script><script>alert(1)</script>")


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
