from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, OrderAction, OrderItem, Table

User = get_user_model()


class VoidItemTests(TestCase):
    """T16 — void_item() (RF-6)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_void", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item1 = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )
        self.item2 = services.add_item(
            self.order, name="Te helado", price=Decimal("3.00")
        )
        services.send_order(self.order)

    def test_voiding_an_item_requires_reason_and_keeps_the_line(self):
        services.void_item(self.order, self.item1, self.waiter, "Pedido por error")
        self.item1.refresh_from_db()
        self.assertTrue(self.item1.is_voided)
        self.assertEqual(self.item1.void_reason, "Pedido por error")
        self.assertTrue(OrderItem.objects.filter(pk=self.item1.pk).exists())

    def test_voided_items_are_excluded_from_the_total(self):
        services.void_item(self.order, self.item1, self.waiter, "Pedido por error")
        active_total = sum(
            i.unit_price * i.quantity
            for i in self.order.items.filter(is_voided=False)
        )
        self.assertEqual(active_total, Decimal("3.00"))

    def test_voiding_an_item_not_in_progress_is_rejected(self):
        self.order.status = Order.Status.DRAFT
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.void_item(self.order, self.item1, self.waiter, "motivo")

    def test_voiding_leaves_an_order_action_row(self):
        services.void_item(self.order, self.item1, self.waiter, "Pedido por error")
        action = OrderAction.objects.get(
            order=self.order, action_type=OrderAction.ActionType.ITEM_VOIDED
        )
        self.assertEqual(action.performed_by, self.waiter)
        self.assertEqual(action.reason, "Pedido por error")
        self.assertEqual(action.item, self.item1)


class VoidLastItemAutoVoidsOrderTests(TestCase):
    """T17 — anulación automática del pedido completo (RF-6, RF-11)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_auto", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )
        services.send_order(self.order)

    def test_voiding_the_last_active_item_voids_the_whole_order(self):
        services.void_item(self.order, self.item, self.waiter, "Se canceló todo")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.VOIDED)

    def test_voiding_the_last_active_item_frees_the_table(self):
        services.void_item(self.order, self.item, self.waiter, "Se canceló todo")
        table = Table.objects.get(number=1)
        self.assertEqual(table.status, Table.Status.FREE)

    def test_auto_void_reuses_the_same_waiter_and_reason(self):
        services.void_item(self.order, self.item, self.waiter, "Se canceló todo")
        auto_action = OrderAction.objects.get(
            order=self.order, action_type=OrderAction.ActionType.ORDER_VOIDED_AUTO
        )
        self.assertEqual(auto_action.performed_by, self.waiter)
        self.assertEqual(auto_action.reason, "Se canceló todo")

    def test_voiding_one_of_two_items_does_not_auto_void(self):
        item2 = services.add_item(self.order, name="Te", price=Decimal("2.00"))
        services.void_item(self.order, self.item, self.waiter, "motivo")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.IN_PROGRESS)
