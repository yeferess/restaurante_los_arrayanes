from django.test import TestCase

from apps.payments.models import PaymentAccount


class SeedEfectivoMigrationTests(TestCase):
    """T04 — the fixed "Efectivo" account is seeded by a data migration,
    present from the very first `migrate` (RF-2)."""

    def test_efectivo_account_exists_and_is_fixed(self):
        accounts = PaymentAccount.objects.filter(name="Efectivo", is_fixed=True)
        self.assertEqual(accounts.count(), 1)
