"""Reuses apps.orders' IsAdmin — every endpoint here is admin-exclusive
(RF-8)."""

from apps.orders.permissions import IsAdmin

__all__ = ["IsAdmin"]
