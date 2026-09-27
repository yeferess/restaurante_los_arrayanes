from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.menu.models import Category, Product


class CategoryModelTests(TestCase):
    """T03 — `Category` model (RF-1)."""

    def test_creating_a_category_sets_normalized_name_lowercase(self):
        category = Category.objects.create(name="Bebidas")
        self.assertEqual(category.normalized_name, "bebidas")

    def test_normalized_name_is_unique_even_with_different_capitalization(self):
        Category.objects.create(name="Bebidas")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="BEBIDAS")


class ProductModelTests(TestCase):
    """T04 — `Product` model (RF-2, RF-3, RF-4, NFR precisión monetaria)."""

    def setUp(self):
        self.category = Category.objects.create(name="Bebidas")

    def test_creating_a_product_sets_normalized_name_lowercase(self):
        product = Product.objects.create(
            name="Limonada Natural", category=self.category, price=Decimal("4.50")
        )
        self.assertEqual(product.normalized_name, "limonada natural")

    def test_normalized_name_is_unique_even_with_different_capitalization(self):
        Product.objects.create(
            name="Limonada Natural", category=self.category, price=Decimal("4.50")
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    name="LIMONADA NATURAL",
                    category=self.category,
                    price=Decimal("5.00"),
                )

    def test_price_keeps_two_decimal_places(self):
        product = Product.objects.create(
            name="Cafe", category=self.category, price=Decimal("2.35")
        )
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal("2.35"))

    def test_is_available_defaults_to_true(self):
        product = Product.objects.create(
            name="Te helado", category=self.category, price=Decimal("3.00")
        )
        self.assertTrue(product.is_available)

    def test_deleting_a_category_with_a_product_assigned_raises_protected_error(self):
        Product.objects.create(
            name="Jugo de naranja", category=self.category, price=Decimal("3.50")
        )
        with self.assertRaises(ProtectedError):
            self.category.delete()
