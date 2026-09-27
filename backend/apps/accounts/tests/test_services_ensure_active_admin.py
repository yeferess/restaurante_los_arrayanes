from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.services import ensure_active_admin_remains

User = get_user_model()


class EnsureActiveAdminRemainsTests(TestCase):
    """T18 — never allow the system to end up with zero active admins (RF-6)."""

    def test_deactivating_the_only_active_admin_is_rejected(self):
        only_admin = User.objects.create_user(
            username="unico_admin", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        with self.assertRaises(ValidationError):
            ensure_active_admin_remains(excluding=only_admin)

    def test_deactivating_one_of_two_active_admins_is_allowed(self):
        admin_a = User.objects.create_user(
            username="admin_a", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        User.objects.create_user(
            username="admin_b", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        ensure_active_admin_remains(excluding=admin_a)  # should not raise

    def test_no_exclusion_passes_while_at_least_one_admin_is_active(self):
        User.objects.create_user(
            username="admin_solo", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        ensure_active_admin_remains()  # should not raise

    def test_inactive_admins_do_not_count_towards_the_minimum(self):
        active_admin = User.objects.create_user(
            username="admin_activo", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        inactive_admin = User.objects.create_user(
            username="admin_inactivo", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        inactive_admin.is_active = False
        inactive_admin.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            ensure_active_admin_remains(excluding=active_admin)
