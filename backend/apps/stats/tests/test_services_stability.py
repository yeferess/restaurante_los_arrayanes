import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.orders import services as order_services
from apps.payments.models import Payment, PaymentAccount
from apps.payments.services import charge_order, void_charge
from apps.stats.services import _qualifying_payments

User = get_user_model()


def _local(year, month, day, hour=12):
    """A tz-aware instant at `hour` local time on the given local date."""
    naive = datetime.datetime(year, month, day, hour)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class QualifyingPaymentsTests(TestCase):
    """T03 — _qualifying_payments(): stability of already-closed days
    (RF-10)."""

    def setUp(self):
        order_services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_stats_q", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_stats_q", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _charge(self, day):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("10000.00"))
        order_services.send_order(order)
        payment = charge_order(order, self.admin, self.account)
        Payment.objects.filter(pk=payment.pk).update(charged_at=_local(*day))
        return Payment.objects.get(pk=payment.pk)

    def test_active_payment_within_range_qualifies(self):
        self._charge((2026, 3, 10))
        qualifying = _qualifying_payments(
            datetime.date(2026, 3, 10), datetime.date(2026, 3, 10)
        )
        self.assertEqual(qualifying.count(), 1)

    def test_payment_outside_range_does_not_qualify(self):
        self._charge((2026, 3, 9))
        qualifying = _qualifying_payments(
            datetime.date(2026, 3, 10), datetime.date(2026, 3, 10)
        )
        self.assertEqual(qualifying.count(), 0)

    def test_voided_the_same_day_does_not_qualify(self):
        payment = self._charge((2026, 3, 10))
        payment.order.refresh_from_db()
        void_charge(payment.order, self.admin, "Cuenta equivocada")
        Payment.objects.filter(pk=payment.pk).update(
            voided_at=_local(2026, 3, 10, hour=18)
        )
        qualifying = _qualifying_payments(
            datetime.date(2026, 3, 10), datetime.date(2026, 3, 10)
        )
        self.assertEqual(qualifying.count(), 0)

    def test_voided_the_next_day_still_qualifies_for_the_original_day(self):
        payment = self._charge((2026, 3, 10))
        payment.order.refresh_from_db()
        void_charge(payment.order, self.admin, "Cuenta equivocada")
        Payment.objects.filter(pk=payment.pk).update(
            voided_at=_local(2026, 3, 11, hour=9)
        )
        qualifying = _qualifying_payments(
            datetime.date(2026, 3, 10), datetime.date(2026, 3, 10)
        )
        self.assertEqual(qualifying.count(), 1)
