"""Reuses apps.orders' object-level owner check (RF-11) — the same
notion of "owner" 003 already enforces on every other order endpoint."""

from apps.orders.permissions import IsMesero, IsOrderOwner

__all__ = ["IsMesero", "IsOrderOwner"]
