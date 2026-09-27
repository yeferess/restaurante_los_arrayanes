from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.orders.models import Order

User = get_user_model()


class OrderModelTests(TestCase):
    """T04 — `Order` model (RF-2, RF-5, RF-8, RF-9, RF-11)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_ord", password="1234", role=User.Role.MESERO
        )

    def test_creating_an_order_defaults_to_draft_and_not_delivered(self):
        order = Order.objects.create(table_number=1, waiter=self.waiter)
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertFalse(order.delivered)

    def test_status_choices(self):
        order = Order.objects.create(
            table_number=1, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        order.status = Order.Status.CHARGED
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CHARGED)

    def test_table_number_is_a_plain_field_not_a_foreign_key(self):
        order = Order.objects.create(table_number=99, waiter=self.waiter)
        self.assertEqual(order.table_number, 99)
