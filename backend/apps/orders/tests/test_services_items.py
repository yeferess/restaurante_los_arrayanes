from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order, OrderItem

User = get_user_model()


class RemoveItemTests(TestCase):
    """T10 — remove_item(): quitar ítem en borrador (RF-2)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_remove", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = OrderItem.objects.create(
            order=self.order, name="Limonada", unit_price=Decimal("4.50")
        )

    def test_removing_an_item_in_draft_deletes_the_line(self):
        services.remove_item(self.order, self.item)
        self.assertFalse(OrderItem.objects.filter(pk=self.item.pk).exists())

    def test_removing_an_item_when_not_draft_is_rejected(self):
        self.order.status = Order.Status.IN_PROGRESS
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.remove_item(self.order, self.item)
        self.assertTrue(OrderItem.objects.filter(pk=self.item.pk).exists())
