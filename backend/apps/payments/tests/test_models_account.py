from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.payments.models import PaymentAccount


class PaymentAccountModelTests(TestCase):
    """T03 — `PaymentAccount` model (RF-2)."""

    def test_creating_an_account_defaults_to_not_fixed(self):
        account = PaymentAccount.objects.create(name="Nequi #1234")
        self.assertFalse(account.is_fixed)
        self.assertIsNotNone(account.created_at)

    def test_name_must_be_unique(self):
        PaymentAccount.objects.create(name="Nequi #1234")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentAccount.objects.create(name="Nequi #1234")

    def test_can_create_a_fixed_account(self):
        account = PaymentAccount.objects.create(name="Datafono fijo", is_fixed=True)
        self.assertTrue(account.is_fixed)
