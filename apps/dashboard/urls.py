from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("stock/in/", views.stock_in, name="stock_in"),
    path("stock/out/", views.stock_out, name="stock_out"),
    path("stock/adjust/", views.stock_adjust, name="stock_adjust"),
    path("stock/history/", views.stock_history, name="stock_history"),
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/toggle/", views.user_toggle_active, name="user_toggle"),
    path("settings/", views.settings_view, name="settings"),
]
