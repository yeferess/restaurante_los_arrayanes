from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Table

User = get_user_model()


class ReleaseTableTests(TestCase):
    """T21 — release_table() (RF-10). Charging itself now lives in
    005-cobro (apps.payments) — here we only need a "pagada" table,
    set up directly rather than through a real charge."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_release", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_release",
            password="1234",
            role=User.Role.MESERO,
        )
        self.admin = User.objects.create_user(
            username="admin_release", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        table = Table.objects.get(number=1)
        table.status = Table.Status.PAID
        table.save(update_fields=["status"])

    def test_any_waiter_can_release_a_paid_table(self):
        services.release_table(table_number=1)
        table = Table.objects.get(number=1)
        self.assertEqual(table.status, Table.Status.FREE)

    def test_releasing_a_table_that_is_not_paid_is_rejected(self):
        services.resize_tables(2)
        with self.assertRaises(ValidationError):
            services.release_table(table_number=2)

    def test_releasing_a_nonexistent_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.release_table(table_number=999)
