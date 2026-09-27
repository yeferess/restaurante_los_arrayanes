"""Reuses apps.accounts' role permissions instead of duplicating them (RF-8)."""

from apps.accounts.permissions import IsAdmin, IsMesero

__all__ = ["IsAdmin", "IsMesero"]
