from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders.models import Order
from apps.payments import services
from apps.payments.models import Payment, PaymentAccount

User = get_user_model()


class CreateAccountTests(TestCase):
    """T06 — create_account() (RF-2)."""

    def test_creates_an_account_with_the_given_name(self):
        account = services.create_account("Nequi #1234")
        self.assertEqual(account.name, "Nequi #1234")
        self.assertFalse(account.is_fixed)

    def test_rejects_an_empty_name(self):
        with self.assertRaises(ValidationError):
            services.create_account("")

    def test_rejects_a_name_already_used_by_another_account(self):
        services.create_account("Nequi #1234")
        with self.assertRaises(ValidationError):
            services.create_account("Nequi #1234")

    def test_rejects_a_name_already_used_by_efectivo(self):
        with self.assertRaises(ValidationError):
            services.create_account("Efectivo")


class DeleteAccountTests(TestCase):
    """T07 — delete_account() (RF-2)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_acc", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_acc", password="clave1234", role=User.Role.ADMIN
        )
        self.order = Order.objects.create(table_number=1, waiter=self.waiter)

    def test_deletes_an_unused_account(self):
        account = services.create_account("Nequi #1234")
        services.delete_account(account)
        self.assertFalse(PaymentAccount.objects.filter(pk=account.pk).exists())

    def test_rejects_deleting_efectivo(self):
        efectivo = PaymentAccount.objects.get(name="Efectivo")
        with self.assertRaises(ValidationError):
            services.delete_account(efectivo)
        self.assertTrue(PaymentAccount.objects.filter(pk=efectivo.pk).exists())

    def test_rejects_deleting_an_account_already_used_by_a_payment(self):
        account = services.create_account("Nequi #1234")
        Payment.objects.create(
            order=self.order,
            account=account,
            amount=Decimal("10.00"),
            charged_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            services.delete_account(account)
        self.assertTrue(PaymentAccount.objects.filter(pk=account.pk).exists())

    def test_rejects_deleting_an_account_used_only_by_a_voided_payment(self):
        account = services.create_account("Nequi #1234")
        payment = Payment.objects.create(
            order=self.order,
            account=account,
            amount=Decimal("10.00"),
            charged_by=self.admin,
            status=Payment.Status.VOIDED,
        )
        self.assertIsNotNone(payment.pk)
        with self.assertRaises(ValidationError):
            services.delete_account(account)
