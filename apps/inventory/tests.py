from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.services import (
    InsufficientStockError,
    apply_stock_movement,
    create_product_with_initial_stock,
)
from apps.products.models import Category, Product

User = get_user_model()


class InventoryTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass12345",
            role=UserRole.SUPER_ADMIN,
            is_superuser=True,
        )
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="pass12345",
            role=UserRole.MANAGER,
        )
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            role=UserRole.STAFF,
        )
        self.inactive = User.objects.create_user(
            username="inactive",
            password="pass12345",
            role=UserRole.STAFF,
            is_active=False,
        )
        self.cat = Category.objects.create(name="Test Cat")
        self.product = Product.objects.create(
            name="Widget",
            sku="W-001",
            category=self.cat,
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("15.00"),
            quantity=10,
            minimum_stock=2,
        )

    def test_category_creation(self):
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(self.cat.slug, "test-cat")

    def test_product_creation(self):
        self.assertEqual(self.product.sku, "W-001")
        self.assertFalse(self.product.is_low_stock)

    def test_stock_in(self):
        apply_stock_movement(
            product=self.product,
            movement_type=MovementType.IN,
            quantity=5,
            unit_price=Decimal("10"),
            note="",
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 15)
        self.assertEqual(StockMovement.objects.filter(movement_type=MovementType.IN).count(), 1)

    def test_stock_out(self):
        apply_stock_movement(
            product=self.product,
            movement_type=MovementType.OUT,
            quantity=3,
            unit_price=Decimal("15"),
            note="",
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 7)

    def test_insufficient_stock(self):
        with self.assertRaises(InsufficientStockError):
            apply_stock_movement(
                product=self.product,
                movement_type=MovementType.OUT,
                quantity=100,
                unit_price=Decimal("15"),
                note="",
                user=self.manager,
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_adjustment(self):
        apply_stock_movement(
            product=self.product,
            movement_type=MovementType.ADJUSTMENT,
            quantity=4,
            unit_price=Decimal("10"),
            note="count",
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 4)

    def test_adjustment_can_set_stock_to_zero(self):
        movement = apply_stock_movement(
            product=self.product,
            movement_type=MovementType.ADJUSTMENT,
            quantity=0,
            unit_price=Decimal("10"),
            note="zero count",
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 0)
        self.assertEqual(movement.quantity, 0)

    def test_initial_stock_failure_rolls_back_product_creation(self):
        product = Product(
            name="Atomic Widget",
            sku="W-ATOMIC",
            category=self.cat,
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("15.00"),
        )
        with patch(
            "apps.inventory.services.apply_stock_movement",
            side_effect=ValidationError("stock movement failed"),
        ):
            with self.assertRaises(ValidationError):
                create_product_with_initial_stock(
                    product=product,
                    initial_quantity=5,
                    user=self.manager,
                )
        self.assertFalse(Product.objects.filter(sku="W-ATOMIC").exists())

    def test_login_and_dashboard(self):
        logged_in = self.client.login(username="manager", password="pass12345")
        self.assertTrue(logged_in)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)

    def test_login_with_email(self):
        self.assertTrue(self.client.login(username="manager@example.com", password="pass12345"))

    def test_inactive_user_cannot_login(self):
        self.assertFalse(self.client.login(username="inactive", password="pass12345"))

    def test_staff_cannot_create_product(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("dashboard:product_create"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_products(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("dashboard:product_list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_view_users(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("dashboard:user_list"))
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_view_users(self):
        self.client.login(username="manager", password="pass12345")
        response = self.client.get(reverse("dashboard:user_list"))
        self.assertEqual(response.status_code, 403)

    def test_stock_out_form_insufficient(self):
        self.client.login(username="manager", password="pass12345")
        response = self.client.post(
            reverse("dashboard:stock_out"),
            {
                "product": self.product.pk,
                "quantity": 999,
                "unit_price": "15.00",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zaxira yetarli emas")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_stock_adjustment_form_accepts_zero(self):
        self.client.login(username="manager", password="pass12345")
        response = self.client.post(
            reverse("dashboard:stock_adjust"),
            {
                "product": self.product.pk,
                "quantity": 0,
                "unit_price": "10.00",
                "note": "counted empty",
            },
        )

        self.assertRedirects(response, reverse("dashboard:stock_history"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 0)

    def test_api_products_authenticated(self):
        api = APIClient()
        api.force_authenticate(user=self.manager)
        response = api.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_api_products_unauthenticated(self):
        api = APIClient()
        response = api.get("/api/products/")
        self.assertEqual(response.status_code, 401)

    def test_api_stock_in(self):
        api = APIClient()
        api.force_authenticate(user=self.staff)
        response = api.post(
            "/api/stock/in/",
            {"product": self.product.id, "quantity": 2, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 12)

    def test_api_stock_out_insufficient(self):
        api = APIClient()
        api.force_authenticate(user=self.manager)
        response = api.post(
            "/api/stock/out/",
            {"product": self.product.id, "quantity": 999, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_api_stock_adjustment_accepts_zero(self):
        api = APIClient()
        api.force_authenticate(user=self.manager)

        response = api.post(
            "/api/stock/adjust/",
            {"product": self.product.id, "quantity": 0, "unit_price": "10.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 0)

    def test_user_api_enforces_django_password_validators(self):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        payload = {
            "username": "api-created",
            "email": "api-created@example.com",
            "role": UserRole.STAFF,
            "password": "password",
        }

        weak_password = api.post("/api/users/", payload, format="json")
        self.assertEqual(weak_password.status_code, 400)
        self.assertFalse(User.objects.filter(username="api-created").exists())

        payload["password"] = "Very-Different-Api-Password-9274!"
        created = api.post("/api/users/", payload, format="json")
        self.assertEqual(created.status_code, 201)
        user = User.objects.get(username="api-created")
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotEqual(user.password, payload["password"])

        weak_update = api.patch(
            f"/api/users/{user.pk}/",
            {"password": "password"},
            format="json",
        )
        self.assertEqual(weak_update.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password(payload["password"]))

    def test_api_staff_cannot_create_category(self):
        api = APIClient()
        api.force_authenticate(user=self.staff)
        response = api.post("/api/categories/", {"name": "Blocked"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_api_category_delete_with_products_returns_conflict(self):
        api = APIClient()
        api.force_authenticate(user=self.manager)

        response = api.delete(f"/api/categories/{self.cat.pk}/")

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Category.objects.filter(pk=self.cat.pk).exists())

    def test_api_categories_include_product_count(self):
        api = APIClient()
        api.force_authenticate(user=self.manager)

        response = api.get("/api/categories/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["product_count"], 1)

    def test_api_product_delete_with_stock_history_returns_conflict(self):
        apply_stock_movement(
            product=self.product,
            movement_type=MovementType.IN,
            quantity=1,
            unit_price=Decimal("10.00"),
            note="history",
            user=self.manager,
        )
        api = APIClient()
        api.force_authenticate(user=self.manager)

        response = api.delete(f"/api/products/{self.product.pk}/")

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_jwt_token(self):
        api = APIClient()
        response = api.post(
            "/api/auth/token/",
            {"username": "manager", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_jwt_email_token(self):
        api = APIClient()
        response = api.post(
            "/api/auth/token/",
            {"username": "manager@example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_duplicate_sku_api(self):
        api = APIClient()
        api.force_authenticate(user=self.manager)
        response = api.post(
            "/api/products/",
            {
                "name": "Dup",
                "sku": "W-001",
                "category": self.cat.id,
                "purchase_price": "1.00",
                "selling_price": "2.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
