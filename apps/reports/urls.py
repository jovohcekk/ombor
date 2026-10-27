from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_home, name="home"),
    path("export/", views.reports_export_csv, name="export_csv"),
    path("export/pdf/", views.reports_export_pdf, name="export_pdf"),
]
