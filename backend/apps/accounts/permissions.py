from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsAdmin(BasePermission):
    """Grants access only to an authenticated admin account (RF-1)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsMesero(BasePermission):
    """Grants access only to an authenticated mesero account (RF-1)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.MESERO
        )


class IsActingOnOwnAdminAccount(BasePermission):
    """Object-level guard: an admin can only write to their own account.

    No endpoint in this module actually exposes another admin's id as a
    write target (RF-6 keeps that CLI-only), but this permission documents
    and enforces the invariant in depth for whichever view checks it.
    """

    def has_object_permission(self, request, view, obj):
        return obj == request.user
