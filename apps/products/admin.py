from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.products.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "product_count", "created_at")
    search_fields = ("name", "description")
    list_filter = ("created_at",)
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at", "product_count")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(product_total=Count("products"))

    @admin.display(description=_("Products"), ordering="product_total")
    def product_count(self, obj):
        return obj.product_total


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "purchase_price",
        "selling_price",
        "quantity",
        "minimum_stock",
        "stock_status_badge",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "sku", "category__name")
    list_filter = ("category", "is_active", "created_at")
    list_select_related = ("category",)
    ordering = ("name",)
    readonly_fields = ("quantity", "created_at", "updated_at", "stock_status_badge")

    @admin.display(description=_("Stock status"))
    def stock_status_badge(self, obj):
        if obj.quantity <= 0:
            label, status = _("Out of stock"), "out"
        elif obj.quantity <= obj.minimum_stock:
            label, status = _("Low stock"), "low"
        else:
            label, status = _("In stock"), "in"
        return format_html(
            '<span class="stock-status stock-status--{}">{}</span>',
            status,
            label,
        )
