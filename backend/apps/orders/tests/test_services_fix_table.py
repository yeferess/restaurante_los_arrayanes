from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, OrderAction, Table

User = get_user_model()


class FixTableTests(TestCase):
    """T18 — fix_table() (RF-7)."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_fix", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def test_correcting_to_a_free_table(self):
        services.fix_table(self.order, self.waiter, new_table_number=2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.table_number, 2)

    def test_correcting_frees_the_original_table(self):
        services.fix_table(self.order, self.waiter, new_table_number=2)
        original = Table.objects.get(number=1)
        self.assertEqual(original.status, Table.Status.FREE)

    def test_correcting_occupies_the_destination_table(self):
        services.fix_table(self.order, self.waiter, new_table_number=2)
        destination = Table.objects.get(number=2)
        self.assertEqual(destination.status, Table.Status.OCCUPIED)

    def test_owner_never_changes(self):
        services.fix_table(self.order, self.waiter, new_table_number=2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.waiter, self.waiter)

    def test_correcting_to_a_non_free_table_is_rejected(self):
        services.create_order(
            User.objects.create_user(
                username="mesero_other", password="1234", role=User.Role.MESERO
            ),
            table_number=2,
        )
        with self.assertRaises(ValidationError):
            services.fix_table(self.order, self.waiter, new_table_number=2)

    def test_correcting_to_the_same_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.fix_table(self.order, self.waiter, new_table_number=1)

    def test_correcting_to_a_nonexistent_table_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.fix_table(self.order, self.waiter, new_table_number=999)

    def test_correcting_a_charged_order_is_rejected(self):
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.fix_table(self.order, self.waiter, new_table_number=2)

    def test_correcting_leaves_a_table_corrected_action(self):
        services.fix_table(self.order, self.waiter, new_table_number=2)
        action = OrderAction.objects.get(
            order=self.order, action_type=OrderAction.ActionType.TABLE_CORRECTED
        )
        self.assertEqual(action.performed_by, self.waiter)
        self.assertEqual(action.from_table_number, 1)
        self.assertEqual(action.to_table_number, 2)
