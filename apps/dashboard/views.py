import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_POST

from apps.accounts.permissions import manager_required, super_admin_required
from apps.dashboard.forms import (
    CategoryForm,
    ProductForm,
    StockMovementForm,
    UserCreateForm,
    UserForm,
)
from apps.dashboard.services import get_chart_data, get_dashboard_stats
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.services import (
    InsufficientStockError,
    _error_text,
    apply_stock_movement,
    create_product_with_initial_stock,
)
from apps.products.models import Category, Product

User = get_user_model()


def _staff_can_view_products(user):
    return user.can_manage_products or user.role == "staff"


@login_required
def home(request):
    stats = get_dashboard_stats()
    chart = get_chart_data()
    recent = StockMovement.objects.select_related("product", "created_by")[:10]
    low_stock_products = Product.objects.filter(
        is_active=True, quantity__lte=F("minimum_stock")
    ).select_related("category")[:10]
    return render(
        request,
        "dashboard/home.html",
        {
            "stats": stats,
            "chart_json": json.dumps(chart, default=str),
            "recent_movements": recent,
            "low_stock_products": low_stock_products,
        },
    )


@login_required
def product_list(request):
    if not _staff_can_view_products(request.user):
        raise PermissionDenied
    qs = Product.objects.select_related("category").all()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)
    stock_status = request.GET.get("stock")
    if stock_status == "low":
        qs = qs.filter(quantity__lte=F("minimum_stock"))
    elif stock_status == "ok":
        qs = qs.filter(quantity__gt=F("minimum_stock"))
    elif stock_status == "out":
        qs = qs.filter(quantity=0)
    active = request.GET.get("active")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(
        request,
        "products/list.html",
        {
            "page_obj": page,
            "categories": Category.objects.all(),
            "filters": request.GET,
        },
    )


@login_required
def product_detail(request, pk):
    if not _staff_can_view_products(request.user):
        raise PermissionDenied
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    movements = product.movements.select_related("created_by")[:20]
    return render(request, "products/detail.html", {"product": product, "movements": movements})


@login_required
@manager_required
def product_create(request):
    form = ProductForm()
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.quantity = 0
            initial = form.cleaned_data.get("initial_quantity") or 0
            create_product_with_initial_stock(
                product=product, initial_quantity=initial, user=request.user
            )
            messages.success(request, _("Product created."))
            return redirect("dashboard:product_list")
    return render(request, "products/form.html", {"form": form, "title": _("Add Product")})


@login_required
@manager_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(instance=product)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, _("Product updated."))
            return redirect("dashboard:product_list")
    return render(
        request,
        "products/form.html",
        {"form": form, "title": _("Edit Product"), "product": product},
    )


@login_required
@manager_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            product.delete()
            messages.success(request, _("Product deleted."))
        except ProtectedError:
            product.is_active = False
            product.save(update_fields=["is_active"])
            messages.warning(
                request,
                _("Product has stock history and cannot be deleted. It was deactivated instead."),
            )
        return redirect("dashboard:product_list")
    return render(request, "products/delete_confirm.html", {"product": product})


@login_required
@manager_required
def category_list(request):
    categories = Category.objects.annotate(num_products=Count("products"))
    return render(request, "categories/list.html", {"categories": categories})


@login_required
@manager_required
def category_create(request):
    form = CategoryForm()
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Category created."))
            return redirect("dashboard:category_list")
    return render(request, "categories/form.html", {"form": form, "title": _("Add Category")})


@login_required
@manager_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(instance=category)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _("Category updated."))
            return redirect("dashboard:category_list")
    return render(request, "categories/form.html", {"form": form, "title": _("Edit Category")})


@login_required
@manager_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    count = category.products.count()
    if request.method == "POST":
        if count > 0:
            messages.error(
                request,
                ngettext(
                    "Cannot delete this category because %(count)s product uses it.",
                    "Cannot delete this category because %(count)s products use it.",
                    count,
                ) % {"count": count},
            )
            return redirect("dashboard:category_list")
        category.delete()
        messages.success(request, _("Category deleted."))
        return redirect("dashboard:category_list")
    return render(
        request,
        "categories/delete_confirm.html",
        {"category": category, "product_count": count},
    )


def _stock_form_view(request, movement_type, template, title):
    if not request.user.can_manage_stock:
        raise PermissionDenied
    form = StockMovementForm(request.POST or None)
    products = list(
        Product.objects.filter(is_active=True).values(
            "id", "name", "quantity", "purchase_price", "selling_price"
        )
    )
    if request.method == "POST" and form.is_valid():
        product = form.cleaned_data["product"]
        try:
            apply_stock_movement(
                product=product,
                movement_type=movement_type,
                quantity=form.cleaned_data["quantity"],
                unit_price=form.cleaned_data["unit_price"],
                note=form.cleaned_data.get("note", ""),
                user=request.user,
            )
            messages.success(
                request,
                _("%(title)s recorded successfully.") % {"title": title},
            )
            return redirect("dashboard:stock_history")
        except InsufficientStockError as exc:
            form.add_error("quantity", _error_text(exc))
        except ValidationError as exc:
            messages.error(request, _error_text(exc))
    return render(
        request,
        template,
        {
            "form": form,
            "title": title,
            "products_json": json.dumps(products, default=str),
            "movement_type": movement_type,
        },
    )


@login_required
def stock_in(request):
    return _stock_form_view(request, MovementType.IN, "stock/in.html", _("Stock In"))


@login_required
def stock_out(request):
    return _stock_form_view(request, MovementType.OUT, "stock/out.html", _("Stock Out"))


@login_required
@manager_required
def stock_adjust(request):
    return _stock_form_view(
        request, MovementType.ADJUSTMENT, "stock/adjust.html", _("Stock Adjustment")
    )


@login_required
def stock_history(request):
    if not request.user.can_manage_stock and not request.user.can_manage_products:
        raise PermissionDenied
    qs = StockMovement.objects.select_related("product", "created_by")
    mt = request.GET.get("type")
    if mt in MovementType.values:
        qs = qs.filter(movement_type=mt)
    product_id = request.GET.get("product")
    if product_id:
        qs = qs.filter(product_id=product_id)
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "stock/history.html",
        {
            "page_obj": page,
            "movement_types": MovementType.choices,
            "products": Product.objects.filter(is_active=True),
            "filters": request.GET,
        },
    )


@login_required
@super_admin_required
def user_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "users/list.html", {"users": users})


@login_required
@super_admin_required
def user_create(request):
    form = UserCreateForm()
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("User created."))
            return redirect("dashboard:user_list")
    return render(request, "users/form.html", {"form": form, "title": _("Add User")})


@login_required
@super_admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserForm(instance=user)
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("User updated."))
            return redirect("dashboard:user_list")
    return render(
        request, "users/form.html", {"form": form, "title": _("Edit User"), "edit_user": user}
    )


@login_required
@super_admin_required
@require_POST
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, _("You cannot deactivate your own account."))
        return redirect("dashboard:user_list")
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    messages.success(
        request,
        _("User activated.") if user.is_active else _("User deactivated."),
    )
    return redirect("dashboard:user_list")


@login_required
def settings_view(request):
    return render(request, "dashboard/settings.html")


def error_400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
