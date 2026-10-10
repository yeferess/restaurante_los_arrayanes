import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments.models import Payment, PaymentAccount
from apps.payments.services import charge_order
from apps.stats.services import day_summary, range_summary

User = get_user_model()

DAY_1 = datetime.date(2026, 3, 10)
DAY_2 = datetime.date(2026, 3, 11)


def _local(day, hour=12):
    naive = datetime.datetime(day.year, day.month, day.day, hour)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class DaySummaryTests(TestCase):
    """T08 — day_summary() / range_summary() (RF-1 a RF-5)."""

    def setUp(self):
        order_services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_stats_s", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_stats_s", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _charge(self, table_number, day):
        order = order_services.create_order(self.waiter, table_number=table_number)
        order_services.add_item(order, name="Item", price=Decimal("10000.00"))
        order_services.send_order(order)
        Order.objects.filter(pk=order.pk).update(sent_at=_local(day))
        payment = charge_order(order, self.admin, self.account)
        Payment.objects.filter(pk=payment.pk).update(charged_at=_local(day))
        return order

    def test_day_summary_bundles_all_four_metrics(self):
        self._charge(1, DAY_1)
        summary = day_summary(DAY_1)
        self.assertEqual(summary["date"], DAY_1)
        self.assertEqual(summary["money_total"], Decimal("10000.00"))
        self.assertEqual(summary["orders_charged_count"], 1)
        self.assertEqual(
            summary["money_by_account"],
            [{"account_name": "Efectivo", "total": Decimal("10000.00")}],
        )
        self.assertEqual(len(summary["orders_by_waiter"]), 1)
        self.assertEqual(len(summary["top_products"]), 0)

    def test_day_summary_shares_its_money_metrics_with_a_single_day_range(self):
        self._charge(1, DAY_1)
        day = day_summary(DAY_1)
        rng = range_summary(DAY_1, DAY_1)
        self.assertEqual(day["money_total"], rng["money_total"])
        self.assertEqual(day["money_by_account"], rng["money_by_account"])
        self.assertEqual(day["orders_by_waiter"], rng["orders_by_waiter"])
        self.assertEqual(day["top_products"], rng["top_products"])

    def test_range_summary_combines_several_days(self):
        self._charge(1, DAY_1)
        self._charge(2, DAY_2)
        summary = range_summary(DAY_1, DAY_2)
        self.assertEqual(summary["from"], DAY_1)
        self.assertEqual(summary["to"], DAY_2)
        self.assertEqual(summary["money_total"], Decimal("20000.00"))
        self.assertEqual(summary["orders_sent_count"], 2)

    def test_a_future_end_date_does_not_error(self):
        future = datetime.date.today() + datetime.timedelta(days=30)
        summary = range_summary(datetime.date.today(), future)
        self.assertEqual(summary["money_total"], 0)
