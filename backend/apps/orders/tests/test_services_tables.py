from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Table


class ResizeTablesGrowTests(TestCase):
    """T07 — resize_tables(): subir el número de mesas (RF-1)."""

    def test_growing_creates_new_free_tables(self):
        services.resize_tables(3)
        numbers = list(Table.objects.order_by("number").values_list("number", flat=True))
        self.assertEqual(numbers, [1, 2, 3])
        self.assertTrue(all(t.status == Table.Status.FREE for t in Table.objects.all()))

    def test_growing_again_only_adds_the_missing_ones(self):
        services.resize_tables(2)
        services.resize_tables(5)
        numbers = list(Table.objects.order_by("number").values_list("number", flat=True))
        self.assertEqual(numbers, [1, 2, 3, 4, 5])


class ResizeTablesShrinkTests(TestCase):
    """T08 — resize_tables(): bajar el número de mesas (RF-1)."""

    def setUp(self):
        services.resize_tables(6)

    def test_shrinking_removes_the_highest_numbered_tables(self):
        services.resize_tables(5)
        numbers = list(Table.objects.order_by("number").values_list("number", flat=True))
        self.assertEqual(numbers, [1, 2, 3, 4, 5])

    def test_shrinking_is_rejected_if_a_table_to_remove_is_not_free(self):
        Table.objects.filter(number=6).update(status=Table.Status.OCCUPIED)
        with self.assertRaises(ValidationError):
            services.resize_tables(5)
        self.assertEqual(Table.objects.count(), 6)

    def test_cannot_go_below_one(self):
        with self.assertRaises(ValidationError):
            services.resize_tables(0)
