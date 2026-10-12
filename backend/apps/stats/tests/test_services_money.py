import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.orders import services as order_services
from apps.payments.models import Payment, PaymentAccount
from apps.payments.services import charge_order, create_account, void_charge
from apps.stats.services import money_by_account, money_total, orders_charged_count

User = get_user_model()

DAY = datetime.date(2026, 3, 10)


def _local(hour=12, day=DAY):
    naive = datetime.datetime(day.year, day.month, day.day, hour)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class MoneyAggregationTests(TestCase):
    """T04/T05 — money_total(), orders_charged_count(), money_by_account()
    (RF-1, RF-2)."""

    def setUp(self):
        order_services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_stats_m", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_stats_m", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.efectivo = PaymentAccount.objects.get(name="Efectivo")
        self.nequi = create_account("Nequi #1234")

    def _charge(self, table_number, account, price, charged_at=None):
        order = order_services.create_order(self.waiter, table_number=table_number)
        order_services.add_item(order, name="Item", price=Decimal(price))
        order_services.send_order(order)
        payment = charge_order(order, self.admin, account)
        Payment.objects.filter(pk=payment.pk).update(
            charged_at=charged_at or _local()
        )
        return Payment.objects.get(pk=payment.pk)

    def test_money_total_sums_only_qualifying_payments(self):
        self._charge(1, self.efectivo, "10000.00")
        self._charge(2, self.nequi, "20000.00")
        self.assertEqual(money_total(DAY, DAY), Decimal("30000.00"))

    def test_money_total_is_net_of_discounts(self):
        """005 RF-10: a discount lowers what the day actually collected."""
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Item", price=Decimal("10000.00"))
        order_services.send_order(order)
        payment = charge_order(order, self.admin, self.efectivo, discount="2500")
        Payment.objects.filter(pk=payment.pk).update(charged_at=_local())
        self.assertEqual(money_total(DAY, DAY), Decimal("7500.00"))

    def test_orders_charged_count_counts_distinct_orders(self):
        self._charge(1, self.efectivo, "10000.00")
        self._charge(2, self.nequi, "20000.00")
        self.assertEqual(orders_charged_count(DAY, DAY), 2)

    def test_recharging_the_same_order_the_same_day_counts_once(self):
        payment = self._charge(1, self.efectivo, "10000.00")
        order = payment.order
        void_charge(order, self.admin, "Cuenta equivocada")
        Payment.objects.filter(pk=payment.pk).update(voided_at=_local(hour=15))
        order.refresh_from_db()
        second = charge_order(order, self.admin, self.nequi)
        Payment.objects.filter(pk=second.pk).update(charged_at=_local(hour=18))
        self.assertEqual(orders_charged_count(DAY, DAY), 1)
        self.assertEqual(money_total(DAY, DAY), Decimal("10000.00"))

    def test_money_by_account_breaks_down_by_account(self):
        self._charge(1, self.efectivo, "10000.00")
        self._charge(2, self.nequi, "20000.00")
        breakdown = {row["account_name"]: row["total"] for row in money_by_account(DAY, DAY)}
        self.assertEqual(breakdown["Efectivo"], Decimal("10000.00"))
        self.assertEqual(breakdown["Nequi #1234"], Decimal("20000.00"))

    def test_account_without_charges_does_not_appear(self):
        self._charge(1, self.efectivo, "10000.00")
        names = [row["account_name"] for row in money_by_account(DAY, DAY)]
        self.assertNotIn("Nequi #1234", names)
