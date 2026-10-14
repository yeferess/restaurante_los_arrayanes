"""T99 — 003 RF-3, RF-4: a repeated item that hasn't been sent adds up to
its existing line, and each note stays on its own line. 004 RF-6: the
ticket prints one NOTA marker per note line."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.rendering import build_reprint_text
from apps.kitchen_printing.services import print_order
from apps.menu.models import Category, Product
from apps.orders import services
from apps.orders.models import OrderItem

User = get_user_model()


class _Fixture(TestCase):
    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="waiter_merge", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        category = Category.objects.create(name="Platos")
        self.bandeja = Product.objects.create(
            name="Bandeja paisa", category=category, price=Decimal("25000")
        )
        self.ajiaco = Product.objects.create(
            name="Ajiaco", category=category, price=Decimal("20000")
        )
        self.printer = FakePrinterAdapter()
        patcher = patch(
            "apps.kitchen_printing.services.get_printer_adapter",
            side_effect=lambda: self.printer,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _add(self, product, quantity=1, note=""):
        return services.add_item(
            self.order, product_id=product.pk, quantity=quantity, note=note
        )

    def _active_lines(self):
        return list(self.order.items.filter(is_voided=False).order_by("id"))


class MergeInDraftTests(_Fixture):
    def test_repeated_product_adds_quantity_and_stacks_notes(self):
        first = self._add(self.bandeja, quantity=2, note="una sin chorizo")
        self._add(self.ajiaco)
        merged = self._add(self.bandeja, note="sin frijoles")

        self.assertEqual(merged.pk, first.pk)
        lines = self._active_lines()
        self.assertEqual([(line.name, line.quantity) for line in lines],
                         [("Bandeja paisa", 3), ("Ajiaco", 1)])
        self.assertEqual(lines[0].note, "una sin chorizo\nsin frijoles")

    def test_repeat_without_a_note_keeps_the_existing_note(self):
        self._add(self.bandeja, note="sin chorizo")
        merged = self._add(self.bandeja)
        self.assertEqual(merged.quantity, 2)
        self.assertEqual(merged.note, "sin chorizo")

    def test_first_note_comes_from_the_repeat_when_the_line_had_none(self):
        self._add(self.bandeja)
        merged = self._add(self.bandeja, note="sin frijoles")
        self.assertEqual(merged.note, "sin frijoles")

    def test_a_price_change_keeps_a_separate_line(self):
        self._add(self.bandeja)
        self.bandeja.price = Decimal("27000")
        self.bandeja.save()
        self._add(self.bandeja)
        self.assertEqual(len(self._active_lines()), 2)

    def test_off_menu_items_merge_by_name_ignoring_case_and_spaces(self):
        services.add_item(self.order, name="Jugo de mora", price=Decimal("6000"))
        merged = services.add_item(
            self.order, name="  jugo  DE mora ", price=Decimal("6000")
        )
        self.assertEqual(merged.quantity, 2)
        self.assertEqual(len(self._active_lines()), 1)

    def test_off_menu_item_with_another_price_is_not_merged(self):
        services.add_item(self.order, name="Jugo de mora", price=Decimal("6000"))
        services.add_item(self.order, name="Jugo de mora", price=Decimal("7000"))
        self.assertEqual(len(self._active_lines()), 2)

    def test_off_menu_item_never_merges_with_a_catalog_product(self):
        self._add(self.bandeja)
        services.add_item(self.order, name="Bandeja paisa", price=Decimal("25000"))
        self.assertEqual(len(self._active_lines()), 2)

    def test_merged_notes_over_the_cap_are_rejected(self):
        long_note = "x" * services.NOTE_MAX_LENGTH
        for _ in range(services.MERGED_NOTE_MAX_LENGTH // (len(long_note) + 1)):
            self._add(self.bandeja, note=long_note)
        with self.assertRaises(ValidationError):
            self._add(self.bandeja, note=long_note)


class MergeAfterSendingTests(_Fixture):
    def setUp(self):
        super().setUp()
        self._add(self.bandeja, quantity=2, note="una sin chorizo")
        services.send_order(self.order)

    def test_an_addition_never_merges_into_a_sent_line(self):
        addition = self._add(self.bandeja, note="sin frijoles")
        lines = self._active_lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].quantity, 2)
        self.assertEqual(lines[0].note, "una sin chorizo")
        self.assertEqual(addition.line_type, OrderItem.LineType.ADDITION)

    def test_unsent_additions_merge_among_themselves(self):
        self._add(self.bandeja)
        merged = self._add(self.bandeja, note="sin frijoles")
        self.assertEqual(merged.quantity, 2)
        self.assertEqual(len(self._active_lines()), 2)

    def test_a_sent_addition_is_not_merged_again(self):
        self._add(self.bandeja)
        services.send_additions(self.order, self.waiter)
        self._add(self.bandeja)
        self.assertEqual(len(self._active_lines()), 3)

    def test_a_voided_line_never_receives_a_merge(self):
        sent_line = self._active_lines()[0]
        self._add(self.ajiaco)
        services.send_additions(self.order, self.waiter)
        services.void_item(self.order, sent_line, self.waiter, "se equivocó")
        self._add(self.bandeja)
        sent_line.refresh_from_db()
        self.assertEqual(sent_line.quantity, 2)
        self.assertTrue(sent_line.is_voided)


class TicketTests(_Fixture):
    def test_new_order_ticket_shows_one_note_marker_per_line(self):
        self._add(self.bandeja, quantity=2, note="una sin chorizo")
        self._add(self.ajiaco)
        self._add(self.bandeja, note="sin frijoles")
        services.send_order(self.order)
        print_order(self.order, self.waiter)

        ticket = self.printer.printed_texts[0]
        self.assertIn(
            "3x Bandeja paisa\n"
            "   *** NOTA: UNA SIN CHORIZO ***\n"
            "   *** NOTA: SIN FRIJOLES ***\n"
            "1x Ajiaco",
            ticket,
        )

    def test_addition_ticket_shows_only_the_new_quantity(self):
        self._add(self.bandeja, quantity=2)
        services.send_order(self.order)
        print_order(self.order, self.waiter)
        self._add(self.bandeja, note="sin frijoles")
        print_order(self.order, self.waiter)

        ticket = self.printer.printed_texts[1]
        self.assertIn("1x Bandeja paisa\n   *** NOTA: SIN FRIJOLES ***", ticket)
        self.assertNotIn("2x", ticket)

    def test_reprint_shows_every_note_line(self):
        self._add(self.bandeja, note="una sin chorizo")
        self._add(self.bandeja, note="sin frijoles")
        services.send_order(self.order)
        text = build_reprint_text(self.order)
        self.assertIn("*** NOTA: UNA SIN CHORIZO ***", text)
        self.assertIn("*** NOTA: SIN FRIJOLES ***", text)


class AddItemApiTests(_Fixture):
    def test_post_returns_the_merged_line_and_the_total_adds_up(self):
        client = APIClient()
        client.force_authenticate(self.waiter)
        url = f"/api/pedidos/{self.order.id}/items"
        client.post(url, {"product_id": self.bandeja.pk, "quantity": 2}, format="json")
        response = client.post(
            url,
            {"product_id": self.bandeja.pk, "note": "sin frijoles"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["quantity"], 3)
        self.assertEqual(response.data["note"], "sin frijoles")

        detail = client.get(f"/api/pedidos/{self.order.id}").data
        self.assertEqual(len(detail["items"]), 1)
        self.assertEqual(Decimal(detail["total"]), Decimal("75000"))
