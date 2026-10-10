import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.orders.models import DailyOrderCounter, Order

User = get_user_model()


class OrderDailyNumberFieldsTests(TestCase):
    """T71 — `Order.daily_number`/`Order.sent_at` (RF-14)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_dn", password="1234", role=User.Role.MESERO
        )

    def test_defaults_to_null_while_still_a_draft(self):
        order = Order.objects.create(table_number=1, waiter=self.waiter)
        self.assertIsNone(order.daily_number)
        self.assertIsNone(order.sent_at)

    def test_can_be_set_once_sent(self):
        order = Order.objects.create(table_number=1, waiter=self.waiter)
        order.daily_number = 7
        order.sent_at = datetime.datetime.now(datetime.timezone.utc)
        order.save(update_fields=["daily_number", "sent_at"])
        order.refresh_from_db()
        self.assertEqual(order.daily_number, 7)
        self.assertIsNotNone(order.sent_at)


class DailyOrderCounterModelTests(TestCase):
    """T70 — `DailyOrderCounter` (RF-14)."""

    def test_local_date_is_the_primary_key(self):
        counter = DailyOrderCounter.objects.create(local_date=datetime.date(2026, 3, 10))
        self.assertEqual(counter.pk, datetime.date(2026, 3, 10))
        self.assertEqual(counter.last_number, 0)

    def test_last_number_defaults_to_zero(self):
        counter = DailyOrderCounter.objects.create(local_date=datetime.date(2026, 3, 11))
        self.assertEqual(counter.last_number, 0)

    def test_one_row_per_local_date(self):
        DailyOrderCounter.objects.create(local_date=datetime.date(2026, 3, 12))
        with self.assertRaises(Exception):
            DailyOrderCounter.objects.create(local_date=datetime.date(2026, 3, 12))
