import django_filters

from apps.inventory.models import StockMovement


class StockMovementFilter(django_filters.FilterSet):
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = StockMovement
        fields = ["movement_type", "product", "created_after", "created_before"]
