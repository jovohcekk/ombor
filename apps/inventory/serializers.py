from rest_framework import serializers

from apps.inventory.models import MovementType, StockMovement
from apps.inventory.services import InsufficientStockError, _error_text, apply_stock_movement
from apps.products.models import Product


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "movement_type",
            "quantity",
            "unit_price",
            "total_price",
            "note",
            "created_by",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = [
            "total_price",
            "created_by",
            "created_at",
            "movement_type",
        ]


class StockActionSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    note = serializers.CharField(required=False, allow_blank=True)
    movement_type = MovementType.IN

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data.setdefault("note", "")
        try:
            return apply_stock_movement(
                movement_type=self.movement_type,
                user=user,
                **validated_data,
            )
        except InsufficientStockError as exc:
            raise serializers.ValidationError({"quantity": _error_text(exc)})


class StockInSerializer(StockActionSerializer):
    movement_type = MovementType.IN


class StockOutSerializer(StockActionSerializer):
    movement_type = MovementType.OUT


class StockAdjustSerializer(StockActionSerializer):
    movement_type = MovementType.ADJUSTMENT
    quantity = serializers.IntegerField(min_value=0)
