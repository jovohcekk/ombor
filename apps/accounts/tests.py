import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserRole
from apps.products.models import Category, Product

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client.cookies["django_language"] = "en"
        self.user = User.objects.create_user(
            username="demo",
            email="demo@example.com",
            password="pass12345",
            role=UserRole.MANAGER,
        )

    def test_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("register"))

    def test_admin_requires_authentication(self):
        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={reverse('admin:index')}",
            fetch_redirect_response=False,
        )

        landing_page = self.client.get(reverse("admin:index"), follow=True)
        self.assertEqual(landing_page.status_code, 200)
        self.assertEqual(landing_page.request["PATH_INFO"], reverse("admin:login"))
        self.assertContains(landing_page, 'id="login-form"')
        self.assertNotContains(landing_page, 'class="admin-theme-toggle"')
        self.assertNotContains(landing_page, "css/admin.css")
        self.assertNotContains(landing_page, "js/admin-theme.js")
        self.assertNotContains(landing_page, "admin/css/dark_mode.css")
        self.assertNotContains(landing_page, "admin/js/theme.js")
        self.assertContains(landing_page, "css/admin-login.css")

    def test_dashboard_relative_admin_login_url_redirects_to_admin_login(self):
        for path in (
            "/dashboard/manage/login",
            "/dashboard/manage/login/",
            "/dashboard/manage/login?next=/manage/products/product/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)

                expected_url = reverse("admin:login")
                if "?" in path:
                    expected_url = f"{expected_url}?next=/manage/products/product/"
                self.assertRedirects(
                    response,
                    expected_url,
                    fetch_redirect_response=False,
                )

    def test_admin_login_redirects_to_admin_index(self):
        admin_user = User.objects.create_superuser(
            username="admin-demo",
            email="admin-demo@example.com",
            password="AdminPass!4821",
        )

        response = self.client.post(
            reverse("admin:login"),
            {"username": admin_user.username, "password": "AdminPass!4821"},
        )

        self.assertRedirects(
            response,
            reverse("admin:index"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_admin_login_rejects_invalid_password_and_non_staff_user(self):
        invalid_password = self.client.post(
            reverse("admin:login"),
            {"username": self.user.username, "password": "wrong-password"},
        )
        non_staff_user = self.client.post(
            reverse("admin:login"),
            {"username": self.user.username, "password": "pass12345"},
        )

        self.assertEqual(invalid_password.status_code, 200)
        self.assertTrue(invalid_password.context["form"].non_field_errors())
        self.assertEqual(non_staff_user.status_code, 200)
        self.assertTrue(non_staff_user.context["form"].non_field_errors())

    def test_admin_logout_ends_session(self):
        admin_user = User.objects.create_superuser(
            username="admin-logout",
            email="admin-logout@example.com",
            password="AdminPass!4821",
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse("admin:logout"))

        self.assertRedirects(
            response,
            reverse("admin:login"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get(reverse("admin:index")),
            f"{reverse('admin:login')}?next={reverse('admin:index')}",
            fetch_redirect_response=False,
        )

    def test_authentication_pages_do_not_load_admin_theme_assets(self):
        for url in (reverse("login"), reverse("register")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'class="admin-theme-toggle"')
                self.assertNotContains(response, "css/admin.css")
                self.assertNotContains(response, "js/admin-theme.js")

    def test_authenticated_admin_index_shows_theme_toggle(self):
        admin_user = User.objects.create_superuser(
            username="admin-theme",
            email="admin-theme@example.com",
            password="AdminPass!4821",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="admin-theme-toggle"')
        self.assertContains(response, 'aria-label="Toggle dark/light theme"')
        self.assertContains(response, "css/admin.css")
        self.assertContains(response, "js/admin-theme.js")

        product_list = self.client.get(reverse("admin:products_product_changelist"))
        self.assertEqual(product_list.status_code, 200)
        self.assertContains(product_list, 'class="admin-theme-toggle"')
        self.assertContains(product_list, "css/admin.css")

    def test_registration_page(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, reverse("login"))

    def test_registration_creates_hashed_user_and_session(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-user",
                "email": "New.User@example.com",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
            },
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        user = User.objects.get(username="new-user")
        self.assertEqual(user.email, "new.user@example.com")
        self.assertEqual(user.role, UserRole.STAFF)
        self.assertTrue(user.check_password("SafePass!4821"))
        self.assertNotEqual(user.password, "SafePass!4821")
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

        self.client.post(reverse("logout"))
        returning_client = Client()
        response = returning_client.post(
            reverse("login"),
            {"username": "NEW.USER@example.com", "password": "SafePass!4821"},
        )
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertEqual(returning_client.get(reverse("dashboard:home")).status_code, 200)

    def test_registration_rejects_duplicate_username_case_insensitively(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "DEMO",
                "email": "another@example.com",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This username is already registered.")
        self.assertEqual(User.objects.count(), 1)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "another-user",
                "email": "DEMO@EXAMPLE.COM",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This email address is already registered.")
        self.assertEqual(User.objects.count(), 1)

    def test_database_enforces_case_insensitive_username_uniqueness(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="DEMO",
                    email="another@example.com",
                    password="SafePass!4821",
                )

        self.assertEqual(User.objects.count(), 1)

    def test_database_enforces_case_insensitive_email_uniqueness(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="another-user",
                    email="DEMO@EXAMPLE.COM",
                    password="SafePass!4821",
                )

        self.assertEqual(User.objects.count(), 1)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "another-user",
                "email": "another@example.com",
                "password1": "SafePass!4821",
                "password2": "DifferentPass!4821",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two password fields didn’t match.")
        self.assertFalse(User.objects.filter(username="another-user").exists())

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "another-user",
                "email": "another@example.com",
                "password1": "password",
                "password2": "password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This password is too common.")
        self.assertFalse(User.objects.filter(username="another-user").exists())

    def test_registration_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(
            reverse("register"),
            {
                "username": "csrf-user",
                "email": "csrf@example.com",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="csrf-user").exists())

    def test_registration_accepts_valid_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        page = csrf_client.get(reverse("register"))
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode(),
        ).group(1)

        response = csrf_client.post(
            reverse("register"),
            {
                "username": "csrf-user",
                "email": "csrf@example.com",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertTrue(User.objects.filter(username="csrf-user").exists())

    def test_login_with_registered_email_and_password(self):
        response = self.client.post(
            reverse("login"),
            {"username": "DEMO@example.com", "password": "pass12345"},
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

    def test_login_rejects_incorrect_password(self):
        response = self.client.post(
            reverse("login"),
            {"username": "demo", "password": "incorrect-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_is_redirected_from_login_and_registration(self):
        self.client.login(username="demo", password="pass12345")

        self.assertRedirects(self.client.get(reverse("login")), reverse("dashboard:home"))
        self.assertRedirects(
            self.client.get(reverse("register")), reverse("dashboard:home")
        )

    def test_remember_me_sets_persistent_session(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "demo",
                "password": "pass12345",
                "remember_me": "on",
            },
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertEqual(self.client.session.get_expiry_age(), 604800)

    def test_login_without_remember_me_uses_browser_session(self):
        response = self.client.post(
            reverse("login"),
            {"username": "demo", "password": "pass12345"},
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)

    def test_logout_requires_post(self):
        self.client.login(username="demo", password="pass12345")

        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

    def test_logout_post_ends_session(self):
        self.client.login(username="demo", password="pass12345")

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        dashboard_response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(dashboard_response.status_code, 302)
        self.assertTrue(dashboard_response.url.startswith(reverse("login")))

    def test_logout_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(reverse("logout"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(csrf_client.get(reverse("dashboard:home")).status_code, 200)

    def test_language_switch_preserves_page_and_query_and_persists(self):
        current_url = "/login/?next=%2Fdashboard%2F&source=inventory"
        response = self.client.post(
            reverse("set_language"),
            {"language": "ru", "next": current_url},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], current_url)
        self.assertEqual(self.client.cookies["django_language"].value, "ru")

        page = self.client.get(current_url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["LANGUAGE_CODE"], "ru")
        self.assertContains(page, "Войти")
        self.assertContains(page, 'value="ru" selected')
        self.assertContains(page, "O‘zbekcha")
        self.assertContains(page, "Русский")
        self.assertContains(page, "English")

    def test_default_language_is_uzbek(self):
        response = Client().get(reverse("login"))

        self.assertEqual(response.context["LANGUAGE_CODE"], "uz")
        self.assertContains(response, "Kirish")

    def test_authentication_pages_render_in_each_language(self):
        expected_text = {
            "uz": ("Kirish", "Hisobingizni yarating"),
            "ru": ("Войти", "Создайте аккаунт"),
            "en": ("Sign in", "Create your account"),
        }

        for language, (login_text, register_text) in expected_text.items():
            with self.subTest(language=language):
                anonymous_client = Client()
                anonymous_client.cookies["django_language"] = language
                login_response = anonymous_client.get(reverse("login"))
                registration_response = anonymous_client.get(reverse("register"))

                self.assertEqual(login_response.status_code, 200)
                self.assertEqual(registration_response.status_code, 200)
                self.assertContains(login_response, login_text)
                self.assertContains(registration_response, register_text)
                self.assertContains(registration_response, 'name="csrfmiddlewaretoken"')

    def test_authentication_errors_use_the_active_language(self):
        self.client.cookies["django_language"] = "ru"
        duplicate = self.client.post(
            reverse("register"),
            {
                "username": "demo",
                "email": "new@example.com",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
            },
        )
        invalid_login = self.client.post(
            reverse("login"),
            {"username": "demo", "password": "wrong-password"},
        )

        self.assertContains(duplicate, "Это имя пользователя уже зарегистрировано.")
        self.assertContains(invalid_login, "Введите правильные данные")
        self.assertNotContains(invalid_login, "Please enter a correct username")

    def test_registration_success_message_is_localized(self):
        client = Client()
        client.cookies["django_language"] = "ru"
        response = client.post(
            reverse("register"),
            {
                "username": "localized-new-user",
                "email": "localized@example.com",
                "password1": "SafePass!4821",
                "password2": "SafePass!4821",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ваш аккаунт создан.")

    def test_password_help_and_validation_messages_are_localized(self):
        expected_errors = {
            "uz": ("Bu parol juda ko‘p ishlatiladi.", "Kiritilgan parollar bir-biriga mos kelmadi."),
            "ru": ("Введённый пароль слишком широко распространён.", "Введённые пароли не совпадают."),
            "en": ("This password is too common.", "The two password fields didn’t match."),
        }

        for language, (weak_password_error, mismatch_error) in expected_errors.items():
            with self.subTest(language=language):
                client = Client()
                client.cookies["django_language"] = language
                registration_page = client.get(reverse("register"))
                if language != "en":
                    self.assertNotContains(registration_page, "Your password")

                weak_password = client.post(
                    reverse("register"),
                    {
                        "username": f"weak-password-{language}",
                        "email": f"weak-{language}@example.com",
                        "password1": "password",
                        "password2": "password",
                    },
                )
                mismatched_passwords = client.post(
                    reverse("register"),
                    {
                        "username": f"mismatch-password-{language}",
                        "email": f"mismatch-{language}@example.com",
                        "password1": "SafePass!4821",
                        "password2": "DifferentPass!4821",
                    },
                )

                self.assertContains(weak_password, weak_password_error)
                self.assertContains(mismatched_passwords, mismatch_error)

    def test_language_preference_survives_login_and_logout(self):
        self.client.post(reverse("set_language"), {"language": "ru", "next": reverse("login")})
        login_response = self.client.post(
            reverse("login"),
            {"username": "demo", "password": "pass12345"},
        )
        self.assertRedirects(
            login_response,
            reverse("dashboard:home"),
            fetch_redirect_response=False,
        )
        self.assertContains(
            self.client.get(reverse("dashboard:home")),
            "С возвращением!",
        )
        logout_response = self.client.post(reverse("logout"), follow=True)
        self.assertContains(logout_response, "Вы вышли из системы.")

        response = self.client.get(reverse("login"))

        self.assertEqual(response.context["LANGUAGE_CODE"], "ru")
        self.assertContains(response, "Войти")

    def test_language_switch_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        page = csrf_client.get(reverse("login"))
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode(),
        ).group(1)

        denied = csrf_client.post(
            reverse("set_language"),
            {"language": "ru", "next": reverse("login")},
        )
        accepted = csrf_client.post(
            reverse("set_language"),
            {
                "language": "ru",
                "next": reverse("login"),
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(accepted.status_code, 302)
        self.assertEqual(csrf_client.cookies["django_language"].value, "ru")


class LocalizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="localization-admin",
            email="localization@example.com",
            password="SafePass!4821",
            role=UserRole.SUPER_ADMIN,
        )
        self.category = Category.objects.create(name="Sample category")
        self.product = Product.objects.create(
            name="Sample product",
            sku="LOC-001",
            category=self.category,
            purchase_price="10.50",
            selling_price="12.75",
            quantity=10,
            minimum_stock=2,
        )
        self.client.force_login(self.user)

    def test_dashboard_pages_render_in_each_supported_language(self):
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:product_list"),
            reverse("dashboard:product_create"),
            reverse("dashboard:product_detail", args=[self.product.pk]),
            reverse("dashboard:product_edit", args=[self.product.pk]),
            reverse("dashboard:product_delete", args=[self.product.pk]),
            reverse("dashboard:category_list"),
            reverse("dashboard:category_create"),
            reverse("dashboard:category_edit", args=[self.category.pk]),
            reverse("dashboard:category_delete", args=[self.category.pk]),
            reverse("dashboard:stock_in"),
            reverse("dashboard:stock_out"),
            reverse("dashboard:stock_adjust"),
            reverse("dashboard:stock_history"),
            reverse("dashboard:user_list"),
            reverse("dashboard:user_create"),
            reverse("dashboard:user_edit", args=[self.user.pk]),
            reverse("dashboard:settings"),
            reverse("reports:home"),
        ]
        expected_navigation = {
            "uz": "Boshqaruv paneli",
            "ru": "Панель управления",
            "en": "Dashboard",
        }
        expected_javascript = {
            "uz": "Mavjud",
            "ru": "В наличии",
            "en": "On hand",
        }

        for language, navigation in expected_navigation.items():
            with self.subTest(language=language):
                self.client.cookies["django_language"] = language
                for url in urls:
                    with self.subTest(url=url):
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 200, url)
                        self.assertContains(response, f'<html lang="{language}"')
                        self.assertContains(response, 'name="language"')
                        self.assertContains(response, navigation)
                        self.assertEqual(
                            response.context["javascript_translations"]["on_hand"],
                            expected_javascript[language],
                        )
                csv_response = self.client.get(
                    reverse("reports:export_csv"),
                    {"report": "inventory"},
                )
                localized_product_header = {
                    "uz": "Mahsulot",
                    "ru": "Товар",
                    "en": "Product",
                }[language]
                self.assertEqual(csv_response.status_code, 200)
                self.assertIn(localized_product_header.encode(), csv_response.content)
