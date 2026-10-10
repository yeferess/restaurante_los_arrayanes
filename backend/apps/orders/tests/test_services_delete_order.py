from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, OrderItem, Table

User = get_user_model()


class DeleteOrderTests(TestCase):
    """delete_order() — a mesero can discard their own draft outright,
    no reason, no trace (same philosophy as remove_item)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_del", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def test_deletes_a_draft_order_and_frees_the_table(self):
        order_id = self.order.id
        services.delete_order(self.order)
        self.assertFalse(Order.objects.filter(pk=order_id).exists())
        table = Table.objects.get(number=1)
        self.assertEqual(table.status, Table.Status.FREE)

    def test_deletes_its_items_too(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        order_id = self.order.id
        services.delete_order(self.order)
        self.assertEqual(OrderItem.objects.filter(order_id=order_id).count(), 0)

    def test_rejects_deleting_a_sent_order(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        with self.assertRaises(ValidationError):
            services.delete_order(self.order)
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())
