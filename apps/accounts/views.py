from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import FormView
from django.views.decorators.http import require_POST

from apps.dashboard.forms import LoginForm, RegistrationForm


class CustomLoginView(LoginView):
    template_name = "authentication/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember = form.cleaned_data.get("remember_me")
        if not remember:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(86400 * 7)
        messages.success(self.request, _("Welcome back!"))
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("dashboard:home")


class RegistrationView(FormView):
    template_name = "authentication/register.html"
    form_class = RegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error(
                None,
                _("An account with this username or email already exists. "
                  "Please choose different details."),
            )
            return self.form_invalid(form)

        login(self.request, user, backend="apps.accounts.backends.EmailOrUsernameBackend")
        messages.success(self.request, _("Your account has been created."))
        return redirect("dashboard:home")


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, _("You have been logged out."))
    return redirect("login")
