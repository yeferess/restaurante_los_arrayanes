from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class SetDeliveredTests(TestCase):
    """T19 — set_delivered() (RF-8)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_delivered", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def test_marking_delivered_in_draft(self):
        updated = services.set_delivered(self.order, True)
        self.assertTrue(updated.delivered)

    def test_unmarking_delivered(self):
        services.set_delivered(self.order, True)
        updated = services.set_delivered(self.order, False)
        self.assertFalse(updated.delivered)

    def test_marking_delivered_in_progress_or_charged(self):
        self.order.status = Order.Status.IN_PROGRESS
        self.order.save(update_fields=["status"])
        services.set_delivered(self.order, True)
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        updated = services.set_delivered(self.order, False)
        self.assertFalse(updated.delivered)

    def test_marking_delivered_on_a_voided_order_is_rejected(self):
        self.order.status = Order.Status.VOIDED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.set_delivered(self.order, True)
