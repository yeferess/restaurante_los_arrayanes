import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.menu.models import Category, Product
from apps.menu.services import delete_product
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.stats.services import top_products

User = get_user_model()

DAY = datetime.date(2026, 3, 10)


def _local(hour=12, day=DAY):
    naive = datetime.datetime(day.year, day.month, day.day, hour)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class TopProductsTests(TestCase):
    """T07 — top_products() (RF-4)."""

    def setUp(self):
        order_services.resize_tables(5)
        self.waiter = User.objects.create_user(
            username="mesero_stats_p", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")

    def _sent_order(self, table_number):
        order = order_services.create_order(self.waiter, table_number=table_number)
        return order

    def _freeze(self, order):
        Order.objects.filter(pk=order.pk).update(sent_at=_local())
        return Order.objects.get(pk=order.pk)

    def test_counts_catalog_items_sold(self):
        product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("5000.00")
        )
        order = self._sent_order(1)
        order_services.add_item(order, product_id=product.id, quantity=3)
        order_services.send_order(order)
        self._freeze(order)

        result = top_products(DAY, DAY)
        self.assertEqual(result, [{"product_name": "Limonada", "quantity": 3}])

    def test_off_menu_items_are_excluded(self):
        order = self._sent_order(1)
        order_services.add_item(order, name="Postre de la casa", price=Decimal("8000.00"))
        order_services.send_order(order)
        self._freeze(order)

        self.assertEqual(top_products(DAY, DAY), [])

    def test_voided_items_are_excluded(self):
        product = Product.objects.create(
            name="Jugo", category=self.category, price=Decimal("4000.00")
        )
        order = self._sent_order(1)
        item = order_services.add_item(order, product_id=product.id)
        order_services.send_order(order)
        order_services.add_item(order, product_id=product.id)
        order_services.send_additions(order, self.waiter)
        self._freeze(order)
        order_services.void_item(order, item, self.waiter, "Se equivocó")

        result = top_products(DAY, DAY)
        self.assertEqual(result, [{"product_name": "Jugo", "quantity": 1}])

    def test_items_of_a_fully_voided_order_are_excluded(self):
        product = Product.objects.create(
            name="Sancocho", category=self.category, price=Decimal("20000.00")
        )
        order = self._sent_order(1)
        order_services.add_item(order, product_id=product.id)
        order_services.send_order(order)
        self._freeze(order)
        order_services.void_order(order, self.waiter, "Cliente se retiró")

        self.assertEqual(top_products(DAY, DAY), [])

    def test_an_addition_still_counts_for_the_orders_original_send_day(self):
        product = Product.objects.create(
            name="Te", category=self.category, price=Decimal("3000.00")
        )
        order = self._sent_order(1)
        order_services.add_item(order, name="Cubiertos extra", price=Decimal("0.01"))
        order_services.send_order(order)
        self._freeze(order)
        order_services.add_item(order, product_id=product.id)
        order_services.send_additions(order, self.waiter)

        result = top_products(DAY, DAY)
        self.assertEqual(result, [{"product_name": "Te", "quantity": 1}])

    def test_an_unsent_addition_does_not_count(self):
        """003 RF-5: until the waiter sends it, it is not part of the order."""
        product = Product.objects.create(
            name="Tinto", category=self.category, price=Decimal("2000.00")
        )
        order = self._sent_order(1)
        order_services.add_item(order, name="Cubiertos extra", price=Decimal("0.01"))
        order_services.send_order(order)
        self._freeze(order)
        order_services.add_item(order, product_id=product.id)

        self.assertEqual(top_products(DAY, DAY), [])

    def test_a_deleted_product_no_longer_counts(self):
        product = Product.objects.create(
            name="Arepa", category=self.category, price=Decimal("2000.00")
        )
        order = self._sent_order(1)
        order_services.add_item(order, product_id=product.id)
        order_services.send_order(order)
        self._freeze(order)

        delete_product(product)

        self.assertEqual(top_products(DAY, DAY), [])

    def test_returns_at_most_ten(self):
        order_services.resize_tables(11)
        for index in range(11):
            product = Product.objects.create(
                name=f"Producto {index}",
                category=self.category,
                price=Decimal("1000.00"),
            )
            order = self._sent_order(index + 1)
            order_services.add_item(order, product_id=product.id, quantity=index + 1)
            order_services.send_order(order)
            self._freeze(order)

        self.assertLessEqual(len(top_products(DAY, DAY)), 10)
