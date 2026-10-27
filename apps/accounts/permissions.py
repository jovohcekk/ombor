from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django.shortcuts import redirect
from rest_framework.permissions import BasePermission


def role_required(*roles):
    """Decorator for dashboard views."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect("login")
            if user.is_super_admin:
                return view_func(request, *args, **kwargs)
            if user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, _("You do not have permission to access this page."))
            raise PermissionDenied

        return _wrapped

    return decorator


def manager_required(view_func):
    return role_required("manager")(view_func)


def super_admin_required(view_func):
    return role_required("super_admin")(view_func)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsManagerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager


class IsStaffOrAbove(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and (
            u.is_manager or u.role == "staff"
        )
