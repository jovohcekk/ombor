from decimal import Decimal

from django.test import TestCase

from apps.products.models import Category, Product


class ProductModelTests(TestCase):
    def test_low_stock(self):
        cat = Category.objects.create(name="Parts")
        product = Product.objects.create(
            name="Bolt",
            sku="B-1",
            category=cat,
            purchase_price=Decimal("1.00"),
            selling_price=Decimal("2.00"),
            quantity=2,
            minimum_stock=5,
        )
        self.assertTrue(product.is_low_stock)
        self.assertEqual(product.stock_status, "low")
