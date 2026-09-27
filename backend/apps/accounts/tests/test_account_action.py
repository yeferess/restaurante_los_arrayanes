from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class AccountActionModelTests(TestCase):
    """T06 — AccountAction traceability model (RF-11)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_traza", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_trazado",
            password="1234",
            role=User.Role.MESERO,
            created_by=self.admin,
        )

    def test_create_account_action(self):
        action = AccountAction.objects.create(
            account=self.mesero,
            action_type=AccountAction.ActionType.CREATED,
            performed_by=self.admin,
        )
        self.assertEqual(action.account, self.mesero)
        self.assertEqual(action.performed_by, self.admin)
        self.assertEqual(action.action_type, AccountAction.ActionType.CREATED)

    def test_via_cli_defaults_to_false(self):
        action = AccountAction.objects.create(
            account=self.mesero,
            action_type=AccountAction.ActionType.PIN_RESET,
            performed_by=self.admin,
        )
        self.assertFalse(action.via_cli)

    def test_performed_by_can_be_null_for_cli_actions(self):
        action = AccountAction.objects.create(
            account=self.admin,
            action_type=AccountAction.ActionType.AUTO_LOCKED,
            performed_by=None,
            via_cli=True,
        )
        self.assertIsNone(action.performed_by)
        self.assertTrue(action.via_cli)

    def test_timestamp_is_set_automatically(self):
        action = AccountAction.objects.create(
            account=self.mesero,
            action_type=AccountAction.ActionType.ACTIVATED,
            performed_by=self.admin,
        )
        self.assertIsNotNone(action.timestamp)

    def test_action_type_choices(self):
        field = AccountAction._meta.get_field("action_type")
        expected = {
            "CREATED",
            "PIN_RESET",
            "ACTIVATED",
            "DEACTIVATED",
            "UNLOCKED",
            "OWN_PASSWORD_CHANGED",
            "ADMIN_CREATED",
            "ADMIN_PERMANENTLY_DEACTIVATED",
            "ADMIN_RENAMED",
            "AUTO_LOCKED",
        }
        self.assertEqual({value for value, _ in field.choices}, expected)

    def test_account_is_protected_from_deletion(self):
        AccountAction.objects.create(
            account=self.mesero,
            action_type=AccountAction.ActionType.CREATED,
            performed_by=self.admin,
        )
        with self.assertRaises(ProtectedError):
            self.mesero.delete()

    def test_performed_by_is_protected_from_deletion(self):
        AccountAction.objects.create(
            account=self.mesero,
            action_type=AccountAction.ActionType.CREATED,
            performed_by=self.admin,
        )
        with self.assertRaises(ProtectedError):
            self.admin.delete()
