import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.orders import services as order_services
from apps.orders.models import Order
from apps.stats.services import orders_by_waiter, orders_sent_count

User = get_user_model()

DAY = datetime.date(2026, 3, 10)


def _local(hour=12, day=DAY):
    naive = datetime.datetime(day.year, day.month, day.day, hour)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class OrdersByWaiterTests(TestCase):
    """T06 — orders_sent_count(), orders_by_waiter() (RF-3)."""

    def setUp(self):
        order_services.resize_tables(3)
        self.waiter_a = User.objects.create_user(
            username="mesero_stats_a", password="1234", role=User.Role.MESERO
        )
        self.waiter_b = User.objects.create_user(
            username="mesero_stats_b", password="1234", role=User.Role.MESERO
        )

    def _send(self, waiter, table_number):
        order = order_services.create_order(waiter, table_number=table_number)
        order_services.add_item(order, name="Item", price=Decimal("5000.00"))
        order_services.send_order(order)
        Order.objects.filter(pk=order.pk).update(sent_at=_local())
        return Order.objects.get(pk=order.pk)

    def test_counts_all_orders_sent_that_day(self):
        self._send(self.waiter_a, 1)
        self._send(self.waiter_b, 2)
        self.assertEqual(orders_sent_count(DAY, DAY), 2)

    def test_breaks_down_by_waiter(self):
        self._send(self.waiter_a, 1)
        self._send(self.waiter_a, 2)
        self._send(self.waiter_b, 3)
        breakdown = {
            row["waiter_username"]: row["orders_sent"]
            for row in orders_by_waiter(DAY, DAY)
        }
        self.assertEqual(breakdown["mesero_stats_a"], 2)
        self.assertEqual(breakdown["mesero_stats_b"], 1)

    def test_counts_regardless_of_final_status(self):
        order = self._send(self.waiter_a, 1)
        order_services.void_order(order, self.waiter_a, "Cliente se retiró")
        self.assertEqual(orders_sent_count(DAY, DAY), 1)

    def test_a_draft_never_sent_does_not_count(self):
        order_services.create_order(self.waiter_a, table_number=1)
        self.assertEqual(orders_sent_count(DAY, DAY), 0)

    def test_a_waiter_without_orders_does_not_appear(self):
        self._send(self.waiter_a, 1)
        usernames = [row["waiter_username"] for row in orders_by_waiter(DAY, DAY)]
        self.assertNotIn("mesero_stats_b", usernames)
