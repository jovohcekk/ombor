from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.jwt_serializers import EmailOrUsernameTokenObtainPairSerializer
from apps.accounts.views import CustomLoginView, RegistrationView, logout_view


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


admin.site.site_header = "Ombor Admin"
admin.site.site_title = "Ombor Admin"
admin.site.index_title = "Inventory management"


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", RedirectView.as_view(pattern_name="dashboard:home", permanent=False)),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegistrationView.as_view(), name="register"),
    path("logout/", logout_view, name="logout"),
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
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
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
