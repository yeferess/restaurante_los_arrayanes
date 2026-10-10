import threading
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.orders import services
from apps.orders.models import DailyOrderCounter, Order

User = get_user_model()


class AssignDailyNumberTests(TestCase):
    """T72 — _assign_daily_number() (RF-14)."""

    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_dn_assign", password="1234", role=User.Role.MESERO
        )

    def test_first_order_of_the_day_gets_number_one(self):
        order = services.create_order(self.waiter, table_number=1)
        services._assign_daily_number(order)
        self.assertEqual(order.daily_number, 1)
        self.assertIsNotNone(order.sent_at)

    def test_second_order_of_the_day_gets_number_two(self):
        order_a = services.create_order(self.waiter, table_number=1)
        order_b = services.create_order(self.waiter, table_number=2)
        services._assign_daily_number(order_a)
        services._assign_daily_number(order_b)
        self.assertEqual(order_a.daily_number, 1)
        self.assertEqual(order_b.daily_number, 2)

    def test_a_different_local_date_restarts_the_sequence_at_one(self):
        order_today = services.create_order(self.waiter, table_number=1)
        services._assign_daily_number(order_today)
        self.assertEqual(order_today.daily_number, 1)

        order_other_day = services.create_order(self.waiter, table_number=2)
        with patch(
            "apps.orders.services.timezone.localdate",
            return_value=timezone.localdate() + timedelta(days=1),
        ):
            services._assign_daily_number(order_other_day)
        self.assertEqual(order_other_day.daily_number, 1)
        self.assertEqual(DailyOrderCounter.objects.count(), 2)


class AssignDailyNumberConcurrencyTests(TransactionTestCase):
    """T72 — two near-simultaneous assignments never collide (same
    pattern as kitchen_printing's PrintLockSerializationTests)."""

    def test_two_concurrent_assignments_never_produce_the_same_number(self):
        services.resize_tables(2)
        waiter = User.objects.create_user(
            username="mesero_dn_concur", password="1234", role=User.Role.MESERO
        )
        order_a = services.create_order(waiter, table_number=1)
        order_b = services.create_order(waiter, table_number=2)

        errors = []
        results = {}

        def _run(key, order):
            try:
                services._assign_daily_number(order)
                results[key] = order.daily_number
            except Exception as exc:  # pragma: no cover - diagnostic aid
                errors.append(exc)
            finally:
                from django.db import connection

                connection.close()

        t1 = threading.Thread(target=_run, args=("a", order_a))
        t2 = threading.Thread(target=_run, args=("b", order_b))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [])
        self.assertEqual({results["a"], results["b"]}, {1, 2})


class SendOrderAssignsDailyNumberTests(TestCase):
    """T73 — send_order() integrates the assignment (RF-14)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_dn_send", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))

    def test_sending_assigns_daily_number_and_sent_at(self):
        services.send_order(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.daily_number, 1)
        self.assertIsNotNone(self.order.sent_at)

    def test_resending_does_not_change_the_already_assigned_number(self):
        services.send_order(self.order)
        self.order.refresh_from_db()
        first_number = self.order.daily_number
        first_sent_at = self.order.sent_at

        services.send_order(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.daily_number, first_number)
        self.assertEqual(self.order.sent_at, first_sent_at)

    def test_a_draft_never_sent_has_no_daily_number(self):
        self.assertIsNone(self.order.daily_number)
        self.assertIsNone(self.order.sent_at)


class DailyNumberImmutabilityTests(TestCase):
    """T74 — additions, voids and table corrections never touch an
    already-assigned daily_number/sent_at (RF-14)."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_dn_immutable", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )
        services.send_order(self.order)
        self.order.refresh_from_db()
        self.original_number = self.order.daily_number
        self.original_sent_at = self.order.sent_at

    def _assert_unchanged(self):
        self.order.refresh_from_db()
        self.assertEqual(self.order.daily_number, self.original_number)
        self.assertEqual(self.order.sent_at, self.original_sent_at)

    def test_an_addition_does_not_change_it(self):
        services.add_item(self.order, name="Te", price=Decimal("3.00"))
        self._assert_unchanged()

    def test_voiding_an_item_does_not_change_it(self):
        services.add_item(self.order, name="Te", price=Decimal("3.00"))
        services.void_item(self.order, self.item, self.waiter, "Cliente se arrepintió")
        self._assert_unchanged()

    def test_correcting_the_table_does_not_change_it(self):
        services.fix_table(self.order, self.waiter, new_table_number=2)
        self._assert_unchanged()
