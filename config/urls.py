from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.jwt_serializers import EmailOrUsernameTokenObtainPairSerializer
from apps.accounts.views import CustomLoginView, RegistrationView, logout_view


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer
    throttle_classes = [AnonRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AnonRateThrottle]


admin.site.site_header = "Ombor Admin"
admin.site.site_title = "Ombor Admin"
admin.site.index_title = "Inventory management"


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", RedirectView.as_view(pattern_name="dashboard:home", permanent=False)),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegistrationView.as_view(), name="register"),
    path("logout/", logout_view, name="logout"),
    path(
        "manage/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="authentication/password_reset_form.html",
            email_template_name="authentication/password_reset_email.html",
            subject_template_name="authentication/password_reset_subject.txt",
            success_url=reverse_lazy("admin_password_reset_done"),
        ),
        name="admin_password_reset",
    ),
    path(
        "manage/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="authentication/password_reset_done.html",
        ),
        name="admin_password_reset_done",
    ),
    path(
        "manage/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="authentication/password_reset_confirm.html",
            success_url=reverse_lazy("admin_password_reset_complete"),
        ),
        name="admin_password_reset_confirm",
    ),
    path(
        "manage/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="authentication/password_reset_complete.html",
        ),
        name="admin_password_reset_complete",
    ),
    re_path(
        r"^dashboard/manage/login/?$",
        RedirectView.as_view(
            pattern_name="admin:login",
            permanent=False,
            query_string=True,
        ),
    ),
    path("dashboard/", include("apps.dashboard.urls")),
    path("dashboard/reports/", include("apps.reports.urls")),
    path("manage/", admin.site.urls),
    path("api/auth/token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "api/auth/token/refresh/",
        ThrottledTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("api/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "apps.dashboard.views.error_400"
handler403 = "apps.dashboard.views.error_403"
handler404 = "apps.dashboard.views.error_404"
handler500 = "apps.dashboard.views.error_500"
