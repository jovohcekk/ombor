from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext as _

from apps.inventory.models import MovementType, StockMovement
from apps.products.models import Product


class InsufficientStockError(ValidationError):
    pass


def _error_text(exc):
    if getattr(exc, "messages", None):
        return exc.messages[0]
    return str(exc)


@transaction.atomic
def apply_stock_movement(
    *,
    product: Product,
    movement_type: str,
    quantity: int,
    unit_price: Decimal,
    note: str,
    user,
) -> StockMovement:
    product = Product.objects.select_for_update().get(pk=product.pk)

    if quantity < 1:
        raise ValidationError(_("Quantity must be at least 1."))
    if unit_price is None or Decimal(unit_price) < 0:
        raise ValidationError(_("Price cannot be negative."))

    unit_price = Decimal(unit_price)
    total_price = unit_price * quantity

    if movement_type == MovementType.IN:
        Product.objects.filter(pk=product.pk).update(quantity=F("quantity") + quantity)
    elif movement_type == MovementType.OUT:
        updated = Product.objects.filter(pk=product.pk, quantity__gte=quantity).update(
            quantity=F("quantity") - quantity
        )
        if not updated:
            raise InsufficientStockError(_("Insufficient stock"))
    elif movement_type == MovementType.ADJUSTMENT:
        Product.objects.filter(pk=product.pk).update(quantity=quantity)
    else:
        raise ValidationError(_("Invalid movement type."))

    movement = StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
        note=note or "",
        created_by=user,
    )
    product.refresh_from_db()
    return movement


@transaction.atomic
def create_product_with_initial_stock(*, product: Product, initial_quantity: int, user) -> Product:
    product.quantity = 0
    product.save()
    if initial_quantity and initial_quantity > 0:
        apply_stock_movement(
            product=product,
            movement_type=MovementType.IN,
            quantity=initial_quantity,
            unit_price=product.purchase_price,
            note=_("Initial stock"),
            user=user,
        )
    return product
