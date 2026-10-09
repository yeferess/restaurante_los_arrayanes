from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentAccount

User = get_user_model()


class PaymentModelTests(TestCase):
    """T05 — `Payment` model, with a DB-level invariant of at most one
    ACTIVE payment per order (RF-3, RF-6, RF-7)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_pay", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=1, waiter=self.waiter)
        self.admin = User.objects.create_user(
            username="admin_pay", password="clave1234", role=User.Role.ADMIN
        )
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def test_creating_a_payment_defaults_to_active(self):
        payment = Payment.objects.create(
            order=self.order,
            account=self.account,
            amount=Decimal("34.00"),
            charged_by=self.admin,
        )
        self.assertEqual(payment.status, Payment.Status.ACTIVE)
        self.assertIsNotNone(payment.charged_at)
        self.assertIsNone(payment.voided_at)

    def test_a_second_active_payment_for_the_same_order_is_rejected(self):
        Payment.objects.create(
            order=self.order,
            account=self.account,
            amount=Decimal("34.00"),
            charged_by=self.admin,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Payment.objects.create(
                    order=self.order,
                    account=self.account,
                    amount=Decimal("34.00"),
                    charged_by=self.admin,
                )

    def test_a_voided_payment_does_not_block_a_new_active_one(self):
        first = Payment.objects.create(
            order=self.order,
            account=self.account,
            amount=Decimal("34.00"),
            charged_by=self.admin,
        )
        first.status = Payment.Status.VOIDED
        first.voided_by = self.admin
        first.void_reason = "Cuenta equivocada"
        first.save(update_fields=["status", "voided_by", "void_reason"])

        second = Payment.objects.create(
            order=self.order,
            account=self.account,
            amount=Decimal("34.00"),
            charged_by=self.admin,
        )
        self.assertEqual(second.status, Payment.Status.ACTIVE)
