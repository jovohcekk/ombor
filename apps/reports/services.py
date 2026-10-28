import csv
from io import StringIO

from django.utils.translation import gettext as _

from apps.inventory.models import StockMovement
from apps.products.models import Category, Product


def filter_movements_by_date(qs, date_from=None, date_to=None):
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def inventory_rows():
    for p in Product.objects.select_related("category").filter(is_active=True):
        yield [
            p.sku,
            p.name,
            p.category.name,
            p.quantity,
            p.minimum_stock,
            p.purchase_price,
            p.stock_value,
        ]


def movements_csv_rows(movement_type, date_from=None, date_to=None):
    qs = StockMovement.objects.select_related("product", "created_by").filter(
        movement_type=movement_type
    )
    qs = filter_movements_by_date(qs, date_from, date_to)
    for m in qs:
        yield [
            m.created_at.isoformat(),
            m.product.sku,
            m.product.name,
            m.get_movement_type_display(),
            m.quantity,
            m.unit_price,
            m.total_price,
            m.created_by.username if m.created_by else "",
            m.note,
        ]


def product_rows():
    for p in Product.objects.select_related("category").all():
        yield [
            p.sku,
            p.name,
            p.category.name,
            p.purchase_price,
            p.selling_price,
            p.quantity,
            _("Active") if p.is_active else _("Inactive"),
        ]


def category_rows():
    for c in Category.objects.all():
        yield [c.name, c.product_count, c.description[:80]]


def build_csv(headers, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_safe_csv_row(headers))
    for row in rows:
        writer.writerow(_safe_csv_row(row))
    return buffer.getvalue()


def _safe_csv_row(row):
    safe_row = []
    for value in row:
        if isinstance(value, str) and (
            value.startswith(("\t", "\r"))
            or value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
        ):
            value = f"'{value}"
        safe_row.append(value)
    return safe_row
