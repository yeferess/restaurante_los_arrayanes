from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class RecoverAdminAccessCommandTests(TestCase):
    """T33 — `recover_admin_access` management command (RF-7, RF-10)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_recover", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_unlocks_a_locked_admin_immediately(self):
        self.admin.is_locked = True
        self.admin.failed_login_attempts = 5
        self.admin.save(update_fields=["is_locked", "failed_login_attempts"])

        call_command("recover_admin_access", username="admin_recover", stdout=StringIO())

        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_locked)
        self.assertIsNone(self.admin.locked_at)
        self.assertEqual(self.admin.failed_login_attempts, 0)
        self.assertTrue(self.admin.check_password("Sup3rSecreta"))

    def test_resets_the_password_when_provided(self):
        call_command(
            "recover_admin_access",
            username="admin_recover",
            password="NuevaClave9",
            stdout=StringIO(),
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("NuevaClave9"))
        self.assertFalse(self.admin.check_password("Sup3rSecreta"))

    def test_registers_an_unlocked_action_via_cli(self):
        call_command("recover_admin_access", username="admin_recover", stdout=StringIO())
        self.assertTrue(
            AccountAction.objects.filter(
                account=self.admin,
                action_type=AccountAction.ActionType.UNLOCKED,
                performed_by=None,
                via_cli=True,
            ).exists()
        )

    def test_nonexistent_admin_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command("recover_admin_access", username="no_existe", stdout=StringIO())

    def test_weak_new_password_raises_command_error_and_changes_nothing(self):
        with self.assertRaises(CommandError):
            call_command(
                "recover_admin_access",
                username="admin_recover",
                password="weak",
                stdout=StringIO(),
            )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Sup3rSecreta"))
