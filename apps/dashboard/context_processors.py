from django.db.models import F
from django.utils.translation import gettext

from apps.products.models import Product


def dashboard_context(request):
    javascript_translations = {
        "on_hand": gettext("On hand"),
        "purchase": gettext("Purchase"),
        "selling": gettext("Selling"),
        "quantity_minimum": gettext("Quantity must be at least 1."),
        "insufficient_stock": gettext("Insufficient stock"),
        "stock_in": gettext("Stock In"),
        "stock_out": gettext("Stock Out"),
        "active": gettext("Active"),
        "inactive": gettext("Inactive"),
        "low_stock": gettext("Low stock"),
        "products": gettext("Products"),
        "open_navigation": gettext("Open navigation menu"),
        "close_navigation": gettext("Close navigation menu"),
    }
    if not request.user.is_authenticated:
        return {"javascript_translations": javascript_translations}
    low_stock_count = Product.objects.filter(
        is_active=True, quantity__lte=F("minimum_stock")
    ).count()
    return {
        "current_user_role": getattr(request.user, "role", ""),
        "can_manage_users": request.user.can_manage_users,
        "can_manage_products": request.user.can_manage_products,
        "can_manage_stock": request.user.can_manage_stock,
        "can_view_reports": request.user.can_view_reports,
        "low_stock_count": low_stock_count,
        "javascript_translations": javascript_translations,
    }
