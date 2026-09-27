from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import AccountAction
from apps.accounts.services import register_action

User = get_user_model()


class RegisterActionTests(TestCase):
    """T10 — register_action() writes a traceable AccountAction row (RF-11)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_svc", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_svc",
            password="1234",
            role=User.Role.MESERO,
            created_by=self.admin,
        )

    def test_register_action_creates_a_row_with_expected_fields(self):
        action = register_action(
            account=self.mesero,
            action_type=AccountAction.ActionType.CREATED,
            performed_by=self.admin,
        )
        self.assertEqual(AccountAction.objects.count(), 1)
        self.assertEqual(action.account, self.mesero)
        self.assertEqual(action.action_type, AccountAction.ActionType.CREATED)
        self.assertEqual(action.performed_by, self.admin)
        self.assertFalse(action.via_cli)
        self.assertIsNotNone(action.timestamp)

    def test_register_action_supports_cli_actions_without_performer(self):
        action = register_action(
            account=self.admin,
            action_type=AccountAction.ActionType.ADMIN_PERMANENTLY_DEACTIVATED,
            performed_by=None,
            via_cli=True,
        )
        self.assertIsNone(action.performed_by)
        self.assertTrue(action.via_cli)
