from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, Table

User = get_user_model()


class CreateOrderTests(TestCase):
    """T09 — create_order() (RF-2)."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_create", password="1234", role=User.Role.MESERO
        )

    def test_creating_an_order_on_a_free_table(self):
        order = services.create_order(self.waiter, table_number=1)
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertEqual(order.waiter, self.waiter)
        table = Table.objects.get(number=1)
        self.assertEqual(table.status, Table.Status.OCCUPIED)

    def test_creating_an_order_on_a_non_free_table_is_rejected(self):
        services.create_order(self.waiter, table_number=1)
        with self.assertRaises(ValidationError):
            services.create_order(self.waiter, table_number=1)

    def test_creating_an_order_on_a_nonexistent_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_order(self.waiter, table_number=999)
