from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, OrderAction, Table

User = get_user_model()


class VoidOrderTests(TestCase):
    """T22 — void_order() (RF-11)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_vo", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_vo", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))

    def test_voiding_a_draft_order(self):
        services.void_order(self.order, self.admin, "Cliente se fue")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.VOIDED)

    def test_voiding_an_in_progress_order(self):
        services.send_order(self.order)
        services.void_order(self.order, self.admin, "Cliente se fue")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.VOIDED)

    def test_voiding_frees_the_table(self):
        services.void_order(self.order, self.admin, "motivo")
        table = Table.objects.get(number=1)
        self.assertEqual(table.status, Table.Status.FREE)

    def test_voiding_a_charged_order_is_rejected(self):
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.void_order(self.order, self.admin, "motivo")

    def test_voiding_leaves_an_order_action_row(self):
        services.void_order(self.order, self.admin, "Cliente se fue")
        action = OrderAction.objects.get(
            order=self.order, action_type=OrderAction.ActionType.ORDER_VOIDED
        )
        self.assertEqual(action.performed_by, self.admin)
        self.assertEqual(action.reason, "Cliente se fue")
