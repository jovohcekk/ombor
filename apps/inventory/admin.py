from django.contrib import admin

from apps.inventory.models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "movement_type",
        "quantity",
        "unit_price",
        "total_price",
        "created_by",
        "created_at",
    )
    search_fields = ("product__name", "product__sku", "created_by__username", "note")
    list_filter = ("movement_type", "created_at")
    list_select_related = ("product", "created_by")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = (
        "product",
        "movement_type",
        "quantity",
        "unit_price",
        "total_price",
        "note",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
