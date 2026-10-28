from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.accounts.permissions import IsManagerOrAbove, IsStaffOrAbove
from apps.inventory.filters import StockMovementFilter
from apps.inventory.models import StockMovement
from apps.inventory.serializers import (
    StockAdjustSerializer,
    StockInSerializer,
    StockMovementSerializer,
    StockOutSerializer,
)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("product", "created_by")
    serializer_class = StockMovementSerializer
    permission_classes = [IsStaffOrAbove]
    filterset_class = StockMovementFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ["product__name", "product__sku", "note"]
    ordering_fields = ["created_at"]


class StockInCreateView(generics.CreateAPIView):
    serializer_class = StockInSerializer
    permission_classes = [IsStaffOrAbove]


class StockOutCreateView(generics.CreateAPIView):
    serializer_class = StockOutSerializer
    permission_classes = [IsStaffOrAbove]


class StockAdjustCreateView(generics.CreateAPIView):
    serializer_class = StockAdjustSerializer
    permission_classes = [IsManagerOrAbove]
