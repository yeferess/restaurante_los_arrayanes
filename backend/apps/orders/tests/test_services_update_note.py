from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class UpdateItemNoteTests(TestCase):
    """T14 — update_item_note() (RF-4)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_note", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )

    def test_editing_the_note_of_an_active_item(self):
        updated = services.update_item_note(self.item, "sin azúcar")
        self.assertEqual(updated.note, "sin azúcar")

    def test_editing_a_note_over_200_characters_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.update_item_note(self.item, "x" * 201)

    def test_editing_the_note_of_a_voided_item_is_rejected(self):
        self.item.is_voided = True
        self.item.save(update_fields=["is_voided"])
        with self.assertRaises(ValidationError):
            services.update_item_note(self.item, "nueva nota")

    def test_editing_a_note_on_a_charged_order_is_rejected(self):
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.update_item_note(self.item, "nueva nota")
