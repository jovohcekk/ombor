from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserRole

User = get_user_model()


class ReportFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="report-manager",
            password="Report-Manager-Password-3827!",
            role=UserRole.MANAGER,
        )
        self.client.cookies["django_language"] = "en"
        self.client.force_login(self.user)

    def test_invalid_report_filter_shows_validation_error(self):
        response = self.client.get(reverse("reports:home"), {"from": "not-a-date"})

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter a valid date.", status_code=400)

    def test_reversed_report_date_range_is_rejected(self):
        response = self.client.get(
            reverse("reports:home"),
            {"from": "2026-03-10", "to": "2026-03-01"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "The end date must be on or after the start date.",
            status_code=400,
        )

    def test_invalid_export_filters_return_bad_request(self):
        for url in (reverse("reports:export_csv"), reverse("reports:export_pdf")):
            with self.subTest(url=url):
                response = self.client.get(url, {"report": "unknown"})
                self.assertEqual(response.status_code, 400)
                self.assertContains(
                    response,
                    "Invalid report filters.",
                    status_code=400,
                )
