"""Reuses apps.accounts' role permissions (RF-13), plus an object-level
owner check specific to this module."""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions import IsAdmin, IsMesero

__all__ = ["IsAdmin", "IsMesero", "IsOrderOwner"]


class IsOrderOwner(BasePermission):
    """Object-level guard: only the waiter who created the order can act
    on its content (RF-13)."""

    def has_object_permission(self, request, view, obj):
        return obj.waiter_id == request.user.id
