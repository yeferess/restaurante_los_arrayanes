from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.services import attempt_login

User = get_user_model()


class AdminAutoUnlockTests(TestCase):
    """T14 — a locked admin account unlocks itself after 20 minutes (RF-7)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_autounlock", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def _lock(self, minutes_ago):
        self.admin.is_locked = True
        self.admin.locked_at = timezone.now() - timedelta(minutes=minutes_ago)
        self.admin.failed_login_attempts = 5
        self.admin.save(update_fields=["is_locked", "locked_at", "failed_login_attempts"])

    def test_locked_21_minutes_ago_unlocks_and_allows_login(self):
        self._lock(minutes_ago=21)
        result = attempt_login(
            username="admin_autounlock",
            credential="Sup3rSecreta",
            expected_role=User.Role.ADMIN,
        )
        self.assertTrue(result.success)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_locked)
        self.assertIsNone(self.admin.locked_at)
        self.assertEqual(self.admin.failed_login_attempts, 0)

    def test_locked_10_minutes_ago_stays_locked(self):
        self._lock(minutes_ago=10)
        result = attempt_login(
            username="admin_autounlock",
            credential="Sup3rSecreta",
            expected_role=User.Role.ADMIN,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, "locked")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_locked)

    def test_mesero_is_not_auto_unlocked(self):
        mesero = User.objects.create_user(
            username="mesero_autounlock", password="1234", role=User.Role.MESERO
        )
        mesero.is_locked = True
        mesero.locked_at = timezone.now() - timedelta(minutes=60)
        mesero.save(update_fields=["is_locked", "locked_at"])

        result = attempt_login(
            username="mesero_autounlock", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, "locked")
