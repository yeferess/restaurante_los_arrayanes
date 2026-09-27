from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class CreateAdminCommandTests(TestCase):
    """T32 — `create_admin` management command (RF-10)."""

    def test_creates_the_first_admin_on_an_empty_database(self):
        call_command(
            "create_admin",
            username="root_admin",
            password="Sup3rSecreta",
            stdout=StringIO(),
        )
        admin = User.objects.get(username="root_admin")
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.check_password("Sup3rSecreta"))
        self.assertTrue(
            AccountAction.objects.filter(
                account=admin,
                action_type=AccountAction.ActionType.ADMIN_CREATED,
                performed_by=None,
                via_cli=True,
            ).exists()
        )

    def test_running_it_again_creates_an_additional_admin(self):
        call_command(
            "create_admin",
            username="root_admin",
            password="Sup3rSecreta",
            stdout=StringIO(),
        )
        call_command(
            "create_admin",
            username="second_admin",
            password="OtraSegura9",
            stdout=StringIO(),
        )
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 2)

    def test_duplicate_username_raises_command_error(self):
        call_command(
            "create_admin",
            username="root_admin",
            password="Sup3rSecreta",
            stdout=StringIO(),
        )
        with self.assertRaises(CommandError):
            call_command(
                "create_admin",
                username="root_admin",
                password="OtraSegura9",
                stdout=StringIO(),
            )

    def test_weak_password_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "create_admin",
                username="root_admin",
                password="weak",
                stdout=StringIO(),
            )
