"""Reuses apps.accounts' role permissions (RF-13), plus an object-level
owner check specific to this module."""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions import IsAdmin, IsMesero

__all__ = ["IsAdmin", "IsMesero", "IsMeseroOrAdmin", "IsOrderOwner"]


class IsMeseroOrAdmin(BasePermission):
    """RF-18: the owner-side order endpoints — a waiter, or an admin
    taking an order from the computer. Each view still lets anyone act
    only on the orders they created themselves."""

    def has_permission(self, request, view):
        return IsMesero().has_permission(request, view) or IsAdmin().has_permission(
            request, view
        )


class IsOrderOwner(BasePermission):
    """Object-level guard: only the waiter who created the order can act
    on its content (RF-13)."""

    def has_object_permission(self, request, view, obj):
        return obj.waiter_id == request.user.id
