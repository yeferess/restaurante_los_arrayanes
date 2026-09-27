from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, OrderAction, Table

User = get_user_model()


class ChargeOrderTests(TestCase):
    """T20 — charge_order() (RF-9)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_charge", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_charge", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def test_charging_an_occupied_table(self):
        services.charge_order(self.order, self.admin)
        self.order.refresh_from_db()
        table = Table.objects.get(number=1)
        self.assertEqual(self.order.status, Order.Status.CHARGED)
        self.assertEqual(table.status, Table.Status.PAID)

    def test_charging_leaves_an_order_action_without_reason(self):
        services.charge_order(self.order, self.admin)
        action = OrderAction.objects.get(
            order=self.order, action_type=OrderAction.ActionType.CHARGED
        )
        self.assertEqual(action.performed_by, self.admin)
        self.assertIsNone(action.reason)

    def test_charging_a_table_that_is_not_occupied_is_rejected(self):
        services.charge_order(self.order, self.admin)
        with self.assertRaises(ValidationError):
            services.charge_order(self.order, self.admin)


class ReleaseTableTests(TestCase):
    """T21 — release_table() (RF-10)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_release", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_release",
            password="1234",
            role=User.Role.MESERO,
        )
        self.admin = User.objects.create_user(
            username="admin_release", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.charge_order(self.order, self.admin)

    def test_any_waiter_can_release_a_paid_table(self):
        services.release_table(table_number=1)
        table = Table.objects.get(number=1)
        self.assertEqual(table.status, Table.Status.FREE)

    def test_releasing_a_table_that_is_not_paid_is_rejected(self):
        services.resize_tables(2)
        with self.assertRaises(ValidationError):
            services.release_table(table_number=2)

    def test_releasing_a_nonexistent_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.release_table(table_number=999)
