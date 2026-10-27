from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api_views import UserViewSet
from apps.inventory.api_views import (
    StockAdjustCreateView,
    StockInCreateView,
    StockMovementViewSet,
    StockOutCreateView,
)
from apps.products.api_views import CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"stock", StockMovementViewSet, basename="stock")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("stock/in/", StockInCreateView.as_view(), name="api-stock-in"),
    path("stock/out/", StockOutCreateView.as_view(), name="api-stock-out"),
    path("stock/adjust/", StockAdjustCreateView.as_view(), name="api-stock-adjust"),
    path("", include(router.urls)),
]
