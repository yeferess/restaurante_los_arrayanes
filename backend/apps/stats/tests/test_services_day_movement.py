import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments.models import Payment, PaymentAccount
from apps.payments.services import charge_order, void_charge
from apps.stats.services import day_movement

User = get_user_model()

DAY = datetime.date(2026, 3, 10)
NEXT_DAY = datetime.date(2026, 3, 11)


def _local(day, hour=12):
    naive = datetime.datetime(day.year, day.month, day.day, hour)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class DayMovementTests(TestCase):
    """T09 — day_movement() (RF-6)."""

    def setUp(self):
        order_services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_stats_mv", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_stats_mv", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def test_an_empty_day_returns_empty_lists(self):
        movement = day_movement(DAY)
        self.assertEqual(movement["date"], DAY)
        self.assertEqual(movement["orders"], [])
        self.assertEqual(movement["payments"], [])

    def test_lists_an_order_sent_that_day(self):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("5000.00"))
        order_services.send_order(order)
        order.refresh_from_db()
        Order.objects.filter(pk=order.pk).update(sent_at=_local(DAY))

        movement = day_movement(DAY)
        self.assertEqual(len(movement["orders"]), 1)
        row = movement["orders"][0]
        self.assertEqual(row["daily_number"], order.daily_number)
        self.assertEqual(row["waiter"], "mesero_stats_mv")
        self.assertEqual(row["status"], "IN_PROGRESS")
        self.assertEqual(row["total"], Decimal("5000.00"))

    def test_an_additional_item_updates_the_current_total(self):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("5000.00"))
        order_services.send_order(order)
        Order.objects.filter(pk=order.pk).update(sent_at=_local(DAY))
        order_services.add_item(order, name="Postre", price=Decimal("3000.00"))

        movement = day_movement(DAY)
        self.assertEqual(movement["orders"][0]["total"], Decimal("8000.00"))

    def test_lists_a_payment_registered_that_day(self):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("5000.00"))
        order_services.send_order(order)
        payment = charge_order(order, self.admin, self.account)
        Payment.objects.filter(pk=payment.pk).update(charged_at=_local(DAY))

        movement = day_movement(DAY)
        self.assertEqual(len(movement["payments"]), 1)
        row = movement["payments"][0]
        self.assertEqual(row["account_name"], "Efectivo")
        self.assertEqual(row["amount"], Decimal("5000.00"))
        self.assertEqual(row["charged_by"], "admin_stats_mv")
        self.assertEqual(row["status"], "ACTIVE")

    def test_a_voided_payment_appears_only_on_its_original_charge_day(self):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("5000.00"))
        order_services.send_order(order)
        payment = charge_order(order, self.admin, self.account)
        Payment.objects.filter(pk=payment.pk).update(charged_at=_local(DAY))
        order.refresh_from_db()
        void_charge(order, self.admin, "Cuenta equivocada")
        Payment.objects.filter(pk=payment.pk).update(voided_at=_local(NEXT_DAY))

        original_day = day_movement(DAY)
        next_day = day_movement(NEXT_DAY)
        self.assertEqual(len(original_day["payments"]), 1)
        self.assertEqual(original_day["payments"][0]["status"], "VOIDED")
        self.assertEqual(next_day["payments"], [])

    def test_includes_a_fully_voided_order_for_traceability(self):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("5000.00"))
        order_services.send_order(order)
        Order.objects.filter(pk=order.pk).update(sent_at=_local(DAY))
        order_services.void_order(order, self.waiter, "Cliente se retiró")

        movement = day_movement(DAY)
        self.assertEqual(len(movement["orders"]), 1)
        self.assertEqual(movement["orders"][0]["status"], "VOIDED")
