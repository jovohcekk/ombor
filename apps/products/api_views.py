from django.db.models import Count
from django.utils.translation import gettext as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.accounts.permissions import IsManagerOrAbove, IsStaffOrAbove
from apps.products.models import Category, Product
from apps.products.serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.annotate(product_count_value=Count("products")).order_by(
        "name", "pk"
    )
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrAbove]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.products.exists():
            return Response(
                {"detail": _("Cannot delete a category that contains products.")},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "is_active"]
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "sku", "quantity", "created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsStaffOrAbove()]
        return [IsManagerOrAbove()]

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.movements.exists():
            return Response(
                {"detail": _("Cannot delete a product with stock movement history.")},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
