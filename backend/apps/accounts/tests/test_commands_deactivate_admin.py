from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class DeactivateAdminCommandTests(TestCase):
    """T34 — `deactivate_admin` management command (RF-10)."""

    def setUp(self):
        self.admin_a = User.objects.create_user(
            username="admin_deact_a", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.admin_b = User.objects.create_user(
            username="admin_deact_b", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_deactivates_without_deleting_the_row(self):
        call_command("deactivate_admin", username="admin_deact_a", stdout=StringIO())
        self.admin_a.refresh_from_db()
        self.assertFalse(self.admin_a.is_active)
        self.assertTrue(User.objects.filter(pk=self.admin_a.pk).exists())

    def test_invalidates_an_active_session(self):
        session = SessionStore()
        session["placeholder"] = True
        session.save()
        self.admin_a.current_session_key = session.session_key
        self.admin_a.save(update_fields=["current_session_key"])

        call_command("deactivate_admin", username="admin_deact_a", stdout=StringIO())

        self.assertFalse(SessionStore().exists(session.session_key))
        self.admin_a.refresh_from_db()
        self.assertIsNone(self.admin_a.current_session_key)

    def test_traceability_rows_referencing_the_admin_stay_intact(self):
        mesero = User.objects.create_user(
            username="mesero_deact_admin",
            password="1234",
            role=User.Role.MESERO,
            created_by=self.admin_a,
        )
        action = AccountAction.objects.create(
            account=mesero,
            action_type=AccountAction.ActionType.CREATED,
            performed_by=self.admin_a,
        )

        call_command("deactivate_admin", username="admin_deact_a", stdout=StringIO())

        action.refresh_from_db()
        self.assertEqual(action.performed_by, self.admin_a)
        mesero.refresh_from_db()
        self.assertEqual(mesero.created_by, self.admin_a)

    def test_registers_an_admin_permanently_deactivated_action(self):
        call_command("deactivate_admin", username="admin_deact_a", stdout=StringIO())
        self.assertTrue(
            AccountAction.objects.filter(
                account=self.admin_a,
                action_type=AccountAction.ActionType.ADMIN_PERMANENTLY_DEACTIVATED,
                performed_by=None,
                via_cli=True,
            ).exists()
        )

    def test_deactivating_the_only_active_admin_raises_command_error(self):
        call_command("deactivate_admin", username="admin_deact_b", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("deactivate_admin", username="admin_deact_a", stdout=StringIO())
        self.admin_a.refresh_from_db()
        self.assertTrue(self.admin_a.is_active)

    def test_nonexistent_admin_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command("deactivate_admin", username="no_existe", stdout=StringIO())
