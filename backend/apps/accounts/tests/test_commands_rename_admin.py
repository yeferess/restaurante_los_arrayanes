from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class RenameAdminCommandTests(TestCase):
    """T35 — `rename_admin` management command (RF-10)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_old_name", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_renames_to_a_valid_unique_username(self):
        call_command(
            "rename_admin",
            username="admin_old_name",
            new_username="admin_new_name",
            stdout=StringIO(),
        )
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin_new_name")

    def test_registers_an_admin_renamed_action(self):
        call_command(
            "rename_admin",
            username="admin_old_name",
            new_username="admin_new_name",
            stdout=StringIO(),
        )
        self.assertTrue(
            AccountAction.objects.filter(
                account=self.admin,
                action_type=AccountAction.ActionType.ADMIN_RENAMED,
                performed_by=None,
                via_cli=True,
            ).exists()
        )

    def test_rejects_a_name_already_used_by_another_admin(self):
        User.objects.create_user(
            username="admin_taken", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        with self.assertRaises(CommandError):
            call_command(
                "rename_admin",
                username="admin_old_name",
                new_username="admin_taken",
                stdout=StringIO(),
            )
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin_old_name")

    def test_rejects_a_name_already_used_by_a_mesero(self):
        User.objects.create_user(
            username="mesero_taken", password="1234", role=User.Role.MESERO
        )
        with self.assertRaises(CommandError):
            call_command(
                "rename_admin",
                username="admin_old_name",
                new_username="mesero_taken",
                stdout=StringIO(),
            )

    def test_rejects_an_invalid_format(self):
        with self.assertRaises(CommandError):
            call_command(
                "rename_admin",
                username="admin_old_name",
                new_username="ab",
                stdout=StringIO(),
            )

    def test_nonexistent_admin_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "rename_admin",
                username="no_existe",
                new_username="algo_nuevo",
                stdout=StringIO(),
            )

    def test_invalidates_an_active_session(self):
        session = SessionStore()
        session["placeholder"] = True
        session.save()
        self.admin.current_session_key = session.session_key
        self.admin.save(update_fields=["current_session_key"])

        call_command(
            "rename_admin",
            username="admin_old_name",
            new_username="admin_new_name",
            stdout=StringIO(),
        )

        self.assertFalse(SessionStore().exists(session.session_key))
        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.current_session_key)
