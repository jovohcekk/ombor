from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    def get_product_count(self, obj: Category) -> int:
        count = getattr(obj, "product_count_value", None)
        return count if count is not None else obj.products.count()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "product_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    initial_quantity = serializers.IntegerField(write_only=True, required=False, min_value=0)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "category",
            "category_name",
            "description",
            "purchase_price",
            "selling_price",
            "quantity",
            "initial_quantity",
            "minimum_stock",
            "image",
            "is_active",
            "is_low_stock",
            "stock_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Product name cannot be empty."))
        return value.strip()

    def validate_sku(self, value):
        qs = Product.objects.filter(sku=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(_("SKU must be unique."))
        return value

    def validate_purchase_price(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Price cannot be negative."))
        return value

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Price cannot be negative."))
        return value

    def create(self, validated_data):
        from apps.inventory.services import create_product_with_initial_stock

        initial = validated_data.pop("initial_quantity", 0) or 0
        product = Product(**validated_data)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return create_product_with_initial_stock(
            product=product,
            initial_quantity=initial,
            user=user,
        )

    def update(self, instance, validated_data):
        validated_data.pop("initial_quantity", None)
        return super().update(instance, validated_data)
