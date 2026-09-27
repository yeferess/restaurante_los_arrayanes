from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.orders.models import Table


class TableModelTests(TestCase):
    """T03 — `Table` model (RF-1)."""

    def test_creating_a_table_defaults_to_free(self):
        table = Table.objects.create(number=1)
        self.assertEqual(table.status, Table.Status.FREE)

    def test_number_is_unique(self):
        Table.objects.create(number=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Table.objects.create(number=1)

    def test_status_can_be_occupied_or_paid(self):
        table = Table.objects.create(number=1, status=Table.Status.OCCUPIED)
        self.assertEqual(table.status, Table.Status.OCCUPIED)
        table.status = Table.Status.PAID
        table.save()
        table.refresh_from_db()
        self.assertEqual(table.status, Table.Status.PAID)
