from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.permissions import IsAdmin as AccountsIsAdmin
from apps.accounts.permissions import IsMesero as AccountsIsMesero
from apps.orders.permissions import IsAdmin, IsMesero, IsOrderOwner
from apps.orders import services

User = get_user_model()


class OrdersPermissionsReuseTests(TestCase):
    """T24 — reuse apps.accounts.permissions, plus IsOrderOwner (RF-13)."""

    def test_is_admin_is_the_same_class_as_accounts(self):
        self.assertIs(IsAdmin, AccountsIsAdmin)

    def test_is_mesero_is_the_same_class_as_accounts(self):
        self.assertIs(IsMesero, AccountsIsMesero)


class IsOrderOwnerTests(TestCase):
    def setUp(self):
        services.resize_tables(1)
        self.owner = User.objects.create_user(
            username="mesero_owner", password="1234", role=User.Role.MESERO
        )
        self.other = User.objects.create_user(
            username="mesero_other_owner", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.owner, table_number=1)

    def test_owner_has_object_permission(self):
        request = type("Req", (), {"user": self.owner})()
        self.assertTrue(
            IsOrderOwner().has_object_permission(request, None, self.order)
        )

    def test_non_owner_does_not_have_object_permission(self):
        request = type("Req", (), {"user": self.other})()
        self.assertFalse(
            IsOrderOwner().has_object_permission(request, None, self.order)
        )
