from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.menu.models import Category, Product
from apps.orders import services
from apps.orders.models import Order, OrderItem

User = get_user_model()


class AddItemValidationTests(TestCase):
    """T11 — add_item(): validaciones y copia de datos (RF-3, RF-4)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_add", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.50")
        )

    def test_adding_a_catalog_product_copies_name_and_price(self):
        item = services.add_item(self.order, product_id=self.product.pk)
        self.assertEqual(item.name, "Limonada")
        self.assertEqual(item.unit_price, Decimal("4.50"))
        self.assertEqual(item.catalog_product, self.product)

    def test_catalog_item_is_not_reread_after_product_changes(self):
        item = services.add_item(self.order, product_id=self.product.pk)
        self.product.price = Decimal("9.99")
        self.product.name = "Limonada premium"
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.name, "Limonada")
        self.assertEqual(item.unit_price, Decimal("4.50"))

    def test_off_menu_item_requires_name_and_price(self):
        item = services.add_item(
            self.order, name="Postre especial", price=Decimal("6.00")
        )
        self.assertIsNone(item.catalog_product)
        self.assertEqual(item.name, "Postre especial")
        self.assertEqual(item.unit_price, Decimal("6.00"))

    def test_off_menu_item_with_empty_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(self.order, name="   ", price=Decimal("6.00"))

    def test_off_menu_item_with_name_longer_than_100_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(self.order, name="x" * 101, price=Decimal("6.00"))

    def test_off_menu_item_with_zero_price_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(self.order, name="Postre", price=Decimal("0"))

    def test_off_menu_item_with_non_numeric_price_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(self.order, name="Postre", price="gratis")

    def test_off_menu_item_names_can_repeat(self):
        services.add_item(self.order, name="Postre especial", price=Decimal("6.00"))
        item2 = services.add_item(
            self.order, name="Postre especial", price=Decimal("6.00")
        )
        self.assertEqual(item2.name, "Postre especial")

    def test_note_over_200_characters_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(
                self.order,
                product_id=self.product.pk,
                note="x" * 201,
            )

    def test_note_is_optional(self):
        item = services.add_item(self.order, product_id=self.product.pk)
        self.assertEqual(item.note, "")


class AddItemAvailabilityTests(TestCase):
    """T12 — add_item(): revalidación de disponibilidad (RF-3)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_avail", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada",
            category=self.category,
            price=Decimal("4.50"),
            is_available=False,
        )

    def test_adding_an_unavailable_product_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(self.order, product_id=self.product.pk)

    def test_adding_a_nonexistent_product_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_item(self.order, product_id=999999)


class AddItemLineTypeAndStateTests(TestCase):
    """T13 — add_item(): tipo de línea y bloqueo por estado (RF-5)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_line", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.50")
        )

    def test_item_added_in_draft_is_original(self):
        item = services.add_item(self.order, product_id=self.product.pk)
        self.assertEqual(item.line_type, OrderItem.LineType.ORIGINAL)

    def test_item_added_in_progress_is_addition(self):
        self.order.status = Order.Status.IN_PROGRESS
        self.order.save(update_fields=["status"])
        item = services.add_item(self.order, product_id=self.product.pk)
        self.assertEqual(item.line_type, OrderItem.LineType.ADDITION)

    def test_adding_to_a_charged_order_is_rejected(self):
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.add_item(self.order, product_id=self.product.pk)

    def test_adding_to_a_voided_order_is_rejected(self):
        self.order.status = Order.Status.VOIDED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.add_item(self.order, product_id=self.product.pk)
