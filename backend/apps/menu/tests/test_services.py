from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.menu import services
from apps.menu.models import Category, Product


class CategoryUniquenessTests(TestCase):
    """T05 — case-insensitive uniqueness of category names (RF-1)."""

    def test_creating_a_category_with_a_new_name_succeeds(self):
        category = services.create_category("Bebidas")
        self.assertEqual(category.name, "Bebidas")

    def test_creating_a_duplicate_name_is_rejected_ignoring_case(self):
        services.create_category("Bebidas")
        with self.assertRaises(ValidationError):
            services.create_category("BEBIDAS")

    def test_renaming_to_an_existing_name_is_rejected_ignoring_case(self):
        services.create_category("Bebidas")
        postres = services.create_category("Postres")
        with self.assertRaises(ValidationError):
            services.rename_category(postres, "bebidas")

    def test_renaming_a_category_to_its_own_name_with_different_case_succeeds(self):
        category = services.create_category("Bebidas")
        renamed = services.rename_category(category, "BEBIDAS")
        self.assertEqual(renamed.name, "BEBIDAS")


class CategoryNameValidationTests(TestCase):
    """T06 — category name validation (RF-1)."""

    def test_creating_with_an_empty_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_category("   ")

    def test_creating_with_a_name_longer_than_50_characters_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_category("x" * 51)

    def test_creating_with_exactly_50_characters_succeeds(self):
        category = services.create_category("x" * 50)
        self.assertEqual(len(category.name), 50)

    def test_renaming_to_an_empty_name_is_rejected(self):
        category = services.create_category("Bebidas")
        with self.assertRaises(ValidationError):
            services.rename_category(category, "   ")

    def test_renaming_to_a_name_longer_than_50_characters_is_rejected(self):
        category = services.create_category("Bebidas")
        with self.assertRaises(ValidationError):
            services.rename_category(category, "x" * 51)


class DeleteCategoryTests(TestCase):
    """T07 — reject deleting a category with products assigned (RF-1)."""

    def test_deleting_a_category_without_products_succeeds(self):
        category = services.create_category("Bebidas")
        services.delete_category(category)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_deleting_a_category_with_a_product_assigned_is_rejected(self):
        category = services.create_category("Bebidas")
        Product.objects.create(
            name="Limonada", category=category, price=Decimal("4.00")
        )
        with self.assertRaises(ValidationError):
            services.delete_category(category)
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())


class ProductUniquenessTests(TestCase):
    """T08 — case-insensitive uniqueness of product names (RF-2, RF-3)."""

    def setUp(self):
        self.category = services.create_category("Bebidas")

    def test_creating_a_product_with_a_new_name_succeeds(self):
        product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        self.assertEqual(product.name, "Limonada")

    def test_creating_a_duplicate_name_is_rejected_ignoring_case(self):
        services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        with self.assertRaises(ValidationError):
            services.create_product(
                name="LIMONADA", category_id=self.category.pk, price=Decimal("5.00")
            )

    def test_editing_the_name_to_an_existing_one_is_rejected_ignoring_case(self):
        services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        te = services.create_product(
            name="Te helado", category_id=self.category.pk, price=Decimal("3.00")
        )
        with self.assertRaises(ValidationError):
            services.update_product(te, name="limonada")

    def test_editing_a_product_to_keep_its_own_name_succeeds(self):
        product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        updated = services.update_product(product, name="Limonada")
        self.assertEqual(updated.name, "Limonada")


class CreateProductValidationTests(TestCase):
    """T09 — field validation on product creation (RF-2)."""

    def setUp(self):
        self.category = services.create_category("Bebidas")

    def test_creating_with_an_empty_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_product(
                name="   ", category_id=self.category.pk, price=Decimal("4.00")
            )

    def test_creating_with_a_name_longer_than_100_characters_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_product(
                name="x" * 101, category_id=self.category.pk, price=Decimal("4.00")
            )

    def test_creating_with_a_zero_price_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_product(
                name="Limonada", category_id=self.category.pk, price=Decimal("0")
            )

    def test_creating_with_a_negative_price_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_product(
                name="Limonada", category_id=self.category.pk, price=Decimal("-1")
            )

    def test_creating_with_a_non_numeric_price_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_product(
                name="Limonada", category_id=self.category.pk, price="gratis"
            )

    def test_creating_with_a_nonexistent_category_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_product(
                name="Limonada", category_id=999999, price=Decimal("4.00")
            )


class UpdateProductValidationTests(TestCase):
    """T09 — the same field validation applies when editing (RF-3)."""

    def setUp(self):
        self.category = services.create_category("Bebidas")
        self.product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )

    def test_reassigning_to_a_nonexistent_category_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.update_product(self.product, category_id=999999)

    def test_editing_with_a_zero_price_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.update_product(self.product, price=Decimal("0"))


class CreateProductWithoutAnyCategoryTests(TestCase):
    """T10 — reject product creation while zero categories exist (RF-2)."""

    def test_creating_a_product_with_no_categories_at_all_is_rejected(self):
        self.assertEqual(Category.objects.count(), 0)
        with self.assertRaises(ValidationError) as ctx:
            services.create_product(
                name="Limonada", category_id=1, price=Decimal("4.00")
            )
        self.assertEqual(ctx.exception.code, "no_categories")


class ProductAvailabilityTests(TestCase):
    """T11 — toggling availability doesn't touch other fields (RF-4)."""

    def setUp(self):
        self.category = services.create_category("Bebidas")
        self.product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )

    def test_marking_unavailable(self):
        updated = services.set_product_availability(self.product, is_available=False)
        self.assertFalse(updated.is_available)

    def test_marking_available_again(self):
        services.set_product_availability(self.product, is_available=False)
        updated = services.set_product_availability(self.product, is_available=True)
        self.assertTrue(updated.is_available)

    def test_toggling_availability_does_not_change_name_category_or_price(self):
        services.set_product_availability(self.product, is_available=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Limonada")
        self.assertEqual(self.product.category_id, self.category.pk)
        self.assertEqual(self.product.price, Decimal("4.00"))


class DeleteProductTests(TestCase):
    """T12 — permanent product deletion regardless of history (RF-5)."""

    def setUp(self):
        self.category = services.create_category("Bebidas")
        self.product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )

    def test_deleting_a_product_removes_the_row(self):
        services.delete_product(self.product)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_deleting_an_unavailable_product_also_succeeds(self):
        services.set_product_availability(self.product, is_available=False)
        services.delete_product(self.product)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())


class NotifyMenuChangedTests(TestCase):
    """T13 — real-time notification is triggered from the right places,
    and only those places (RF-6)."""

    def setUp(self):
        self.category = services.create_category("Bebidas")

    @patch("apps.menu.services.notify_menu_changed")
    def test_creating_a_category_does_not_notify(self, mock_notify):
        services.create_category("Postres")
        mock_notify.assert_not_called()

    @patch("apps.menu.services.notify_menu_changed")
    def test_renaming_a_category_notifies(self, mock_notify):
        services.rename_category(self.category, "Refrescos")
        mock_notify.assert_called_once()

    @patch("apps.menu.services.notify_menu_changed")
    def test_deleting_an_empty_category_does_not_notify(self, mock_notify):
        services.delete_category(self.category)
        mock_notify.assert_not_called()

    @patch("apps.menu.services.notify_menu_changed")
    def test_creating_a_product_notifies(self, mock_notify):
        services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        mock_notify.assert_called_once()

    @patch("apps.menu.services.notify_menu_changed")
    def test_editing_a_product_notifies(self, mock_notify):
        product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        mock_notify.reset_mock()
        services.update_product(product, price=Decimal("5.00"))
        mock_notify.assert_called_once()

    @patch("apps.menu.services.notify_menu_changed")
    def test_toggling_availability_notifies(self, mock_notify):
        product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        mock_notify.reset_mock()
        services.set_product_availability(product, is_available=False)
        mock_notify.assert_called_once()

    @patch("apps.menu.services.notify_menu_changed")
    def test_deleting_a_product_notifies(self, mock_notify):
        product = services.create_product(
            name="Limonada", category_id=self.category.pk, price=Decimal("4.00")
        )
        mock_notify.reset_mock()
        services.delete_product(product)
        mock_notify.assert_called_once()
