from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.menu.models import Category, Product
from apps.orders.models import Order, OrderItem

User = get_user_model()


class OrderItemModelTests(TestCase):
    """T05 — `OrderItem` model (RF-3, RF-4, RF-5, RF-6)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_item", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=1, waiter=self.waiter)
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.50")
        )

    def test_creating_a_catalog_item_defaults(self):
        item = OrderItem.objects.create(
            order=self.order,
            catalog_product=self.product,
            name=self.product.name,
            unit_price=self.product.price,
        )
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.line_type, OrderItem.LineType.ORIGINAL)
        self.assertFalse(item.is_voided)
        self.assertIsNone(item.void_reason)
        self.assertEqual(item.note, "")

    def test_creating_an_off_menu_item_without_catalog_product(self):
        item = OrderItem.objects.create(
            order=self.order,
            name="Postre especial del día",
            unit_price=Decimal("6.00"),
        )
        self.assertIsNone(item.catalog_product)
        self.assertEqual(item.name, "Postre especial del día")

    def test_deleting_the_catalog_product_does_not_delete_the_line(self):
        item = OrderItem.objects.create(
            order=self.order,
            catalog_product=self.product,
            name=self.product.name,
            unit_price=self.product.price,
        )
        self.product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.catalog_product)
        self.assertEqual(item.name, "Limonada")
        self.assertEqual(item.unit_price, Decimal("4.50"))

    def test_line_type_choices(self):
        item = OrderItem.objects.create(
            order=self.order,
            name="Te helado",
            unit_price=Decimal("3.00"),
            line_type=OrderItem.LineType.ADDITION,
        )
        self.assertEqual(item.line_type, OrderItem.LineType.ADDITION)
