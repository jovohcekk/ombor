from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.products.models import Product


class MovementType(models.TextChoices):
    IN = "IN", _("Stock In")
    OUT = "OUT", _("Stock Out")
    ADJUSTMENT = "ADJUSTMENT", _("Adjustment")


class StockMovement(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=12, choices=MovementType.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.sku} {self.movement_type} {self.quantity}"
