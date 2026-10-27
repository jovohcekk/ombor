from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.inventory.models import MovementType, StockMovement
from apps.products.models import Category, Product


def get_dashboard_stats():
    today = timezone.localdate()
    products = Product.objects.filter(is_active=True)
    total_products = products.count()
    total_categories = Category.objects.count()
    total_stock = products.aggregate(total=Coalesce(Sum("quantity"), 0))["total"] or 0
    low_stock = products.filter(quantity__lte=F("minimum_stock")).count()
    inventory_value = products.aggregate(
        val=Coalesce(Sum(F("quantity") * F("purchase_price")), Decimal("0"))
    )["val"] or Decimal("0")

    today_movements = StockMovement.objects.filter(created_at__date=today)
    today_in = (
        today_movements.filter(movement_type=MovementType.IN).aggregate(
            q=Coalesce(Sum("quantity"), 0)
        )["q"]
        or 0
    )
    today_out = (
        today_movements.filter(movement_type=MovementType.OUT).aggregate(
            q=Coalesce(Sum("quantity"), 0)
        )["q"]
        or 0
    )

    return {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_stock": total_stock,
        "low_stock": low_stock,
        "inventory_value": inventory_value,
        "today_in": today_in,
        "today_out": today_out,
    }


def get_chart_data(days=14):
    now = timezone.now()
    since = now - timedelta(days=days - 1)
    qs = (
        StockMovement.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day", "movement_type")
        .annotate(total=Sum("quantity"))
        .order_by("day")
    )
    by_day = {}
    for row in qs:
        day = row["day"].isoformat() if row["day"] else ""
        by_day.setdefault(day, {"IN": 0, "OUT": 0})
        by_day[day][row["movement_type"]] = int(row["total"] or 0)

    labels = []
    in_data = []
    out_data = []
    start = timezone.localdate() - timedelta(days=days - 1)
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        labels.append(day)
        in_data.append(by_day.get(day, {}).get("IN", 0))
        out_data.append(by_day.get(day, {}).get("OUT", 0))

    category_dist = list(
        Category.objects.annotate(count=Count("products")).values("name", "count")
    )
    product_stats = {
        "active": Product.objects.filter(is_active=True).count(),
        "inactive": Product.objects.filter(is_active=False).count(),
        "low": Product.objects.filter(
            is_active=True, quantity__lte=F("minimum_stock")
        ).count(),
    }
    return {
        "labels": labels,
        "stock_in": in_data,
        "stock_out": out_data,
        "categories": [c["name"] for c in category_dist],
        "category_counts": [c["count"] for c in category_dist],
        "product_stats": product_stats,
    }
