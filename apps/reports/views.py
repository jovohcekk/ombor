from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from apps.inventory.models import MovementType
from apps.products.models import Product
from apps.reports.forms import ReportFilterForm
from apps.reports.pdf import PdfExportNotConfigured, render_report_pdf
from apps.reports.services import (
    build_csv,
    category_rows,
    inventory_rows,
    movements_csv_rows,
    product_rows,
)

INVENTORY_HEADERS = [
    "SKU",
    _("Product"),
    _("Category"),
    _("Qty"),
    _("Min Stock"),
    _("Purchase Price"),
    _("Value"),
]
MOVEMENT_HEADERS = [
    _("Date"),
    "SKU",
    _("Product"),
    _("Type"),
    _("Qty"),
    _("Unit"),
    _("Total"),
    _("User"),
    _("Note"),
]


def _report_payload(report, date_from, date_to):
    if report == "inventory":
        return INVENTORY_HEADERS, list(inventory_rows())
    if report == "stock_in":
        return MOVEMENT_HEADERS, list(
            movements_csv_rows(MovementType.IN, date_from or None, date_to or None)
        )
    if report == "stock_out":
        return MOVEMENT_HEADERS, list(
            movements_csv_rows(MovementType.OUT, date_from or None, date_to or None)
        )
    if report == "low_stock":
        return ["SKU", _("Product"), _("Category"), _("Qty"), _("Min Stock")], [
            [p.sku, p.name, p.category.name, p.quantity, p.minimum_stock]
            for p in Product.objects.filter(is_active=True)
            .filter(quantity__lte=F("minimum_stock"))
            .select_related("category")
        ]
    if report == "products":
        return [
            "SKU",
            _("Name"),
            _("Category"),
            _("Purchase"),
            _("Selling"),
            _("Qty"),
            _("Active"),
        ], list(product_rows())
    if report == "categories":
        return [_("Category"), _("Products"), _("Description")], list(category_rows())
    return [_("Error")], [[_("Unknown report")]]


def _get_report_filters(request):
    data = request.GET.copy()
    if "report" not in data:
        data["report"] = "inventory"
    data["date_from"] = data.get("from", "")
    data["date_to"] = data.get("to", "")
    form = ReportFilterForm(data)
    return form, form.cleaned_data if form.is_valid() else None


@login_required
def reports_home(request):
    if not request.user.can_view_reports:
        raise PermissionDenied
    form, filters = _get_report_filters(request)
    if filters is None:
        report = request.GET.get("report", "inventory")
        date_from = request.GET.get("from", "")
        date_to = request.GET.get("to", "")
        headers, rows = [], []
        status = 400
    else:
        report = filters["report"]
        date_from = filters["date_from"]
        date_to = filters["date_to"]
        headers, rows = _report_payload(report, date_from, date_to)
        status = 200
    return render(
        request,
        "reports/index.html",
        {
            "form": form,
            "report": report,
            "date_from": date_from,
            "date_to": date_to,
            "headers": headers,
            "rows": rows,
        },
        status=status,
    )


@login_required
def reports_export_csv(request):
    if not request.user.can_view_reports:
        raise PermissionDenied
    filter_form, filters = _get_report_filters(request)
    if filters is None:
        return HttpResponse(
            _("Invalid report filters.") + "\n" + filter_form.errors.as_text(),
            content_type="text/plain",
            status=400,
        )
    report = filters["report"]
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    headers, rows = _report_payload(report, date_from, date_to)
    response = HttpResponse(build_csv(headers, rows), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{report}.csv"'
    return response


@login_required
def reports_export_pdf(request):
    if not request.user.can_view_reports:
        raise PermissionDenied
    filter_form, filters = _get_report_filters(request)
    if filters is None:
        return HttpResponse(
            _("Invalid report filters.") + "\n" + filter_form.errors.as_text(),
            content_type="text/plain",
            status=400,
        )
    report = filters["report"]
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    headers, rows = _report_payload(report, date_from, date_to)
    try:
        pdf_bytes = render_report_pdf(report, headers, rows)
    except PdfExportNotConfigured:
        return HttpResponse(
            _("PDF export is not enabled in this deployment. Use CSV export, or install "
              "WeasyPrint/ReportLab and implement apps.reports.pdf.render_report_pdf."),
            content_type="text/plain",
            status=501,
        )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{report}.pdf"'
    return response
