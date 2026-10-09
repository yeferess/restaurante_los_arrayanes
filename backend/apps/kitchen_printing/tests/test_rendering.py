from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from django.utils import timezone

from apps.kitchen_printing.models import PrintJob
from apps.kitchen_printing.rendering import (
    build_notes_block,
    build_ticket_text,
    format_item_line,
    to_ascii,
)
from apps.orders.models import Order, OrderAction, OrderItem

User = get_user_model()


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class HeaderAndMetadataTests(TestCase):
    """T08 — header and metadata common to every ticket type (RF-2)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="cgarcia", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=5, waiter=self.waiter)

    def test_header_shows_ticket_type_and_table_number(self):
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        self.assertIn("PEDIDO NUEVO - MESA 5", text)

    def test_header_differs_per_ticket_type(self):
        addition = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.ADDITION
        )
        void = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.VOID
        )
        self.assertIn("ADICION - MESA 5", build_ticket_text(addition))
        self.assertIn("ANULACION - MESA 5", build_ticket_text(void))

    def test_includes_order_id_and_waiter_username(self):
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        self.assertIn(f"Pedido #{self.order.id}", text)
        self.assertIn("Mesero: cgarcia", text)

    def test_every_line_fits_within_the_configured_width(self):
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        for line in text.splitlines():
            self.assertLessEqual(len(line), 40)


class ToAsciiTests(TestCase):
    """T09 — ASCII transliteration before anything reaches the printer
    (plan.md, decisión técnica 7)."""

    def test_transliterates_common_spanish_accents_and_enye(self):
        self.assertEqual(to_ascii("á é í ó ú Á É Í Ó Ú"), "a e i o u A E I O U")
        self.assertEqual(to_ascii("ñ Ñ"), "n N")

    def test_leaves_plain_ascii_untouched(self):
        self.assertEqual(to_ascii("Sancocho de gallina"), "Sancocho de gallina")

    def test_handles_a_realistic_note_with_mixed_accents(self):
        self.assertEqual(to_ascii("sin cebolla, poquito limón"), "sin cebolla, poquito limon")


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class NewOrderContentTests(TestCase):
    """T12 — "PEDIDO NUEVO" content: every active item of the order at
    send time (RF-3)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="cgarcia3", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=5, waiter=self.waiter)

    def test_lists_every_active_item(self):
        OrderItem.objects.create(
            order=self.order, name="Limonada natural", unit_price="4.50", quantity=2
        )
        OrderItem.objects.create(
            order=self.order, name="Sancocho de gallina", unit_price="20.00", quantity=1
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        self.assertIn("2x Limonada natural", text)
        self.assertIn("1x Sancocho de gallina", text)

    def test_off_menu_items_are_listed_the_same_way(self):
        OrderItem.objects.create(
            order=self.order, name="Postre de la casa", unit_price="6.00", quantity=1
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        self.assertIn("1x Postre de la casa", build_ticket_text(job))

    def test_voided_items_never_appear(self):
        voided = OrderItem.objects.create(
            order=self.order, name="Jugo de mora", unit_price="5.00", quantity=1
        )
        voided.is_voided = True
        voided.void_reason = "cliente se arrepintio"
        voided.save(update_fields=["is_voided", "void_reason"])
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        self.assertNotIn("Jugo de mora", build_ticket_text(job))

    def test_notes_block_appears_before_the_item_list(self):
        OrderItem.objects.create(
            order=self.order,
            name="Limonada natural",
            unit_price="4.50",
            quantity=1,
            note="sin azucar",
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        self.assertLess(text.index("*** NOTA"), text.index("1x Limonada natural"))


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class DerivedContentSinceLastPrintTests(TestCase):
    """T13 — content derived "since the last successfully printed
    ticket" for ADICIÓN/ANULACIÓN, including the mixed-type case from
    consolidation (RF-4, RF-5, RF-8)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="cgarcia4", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=5, waiter=self.waiter)
        # Simulate an already-printed "PEDIDO NUEVO" ticket in the past,
        # so later items are the ones that count as "new" from here on.
        self.first_item = OrderItem.objects.create(
            order=self.order, name="Sancocho de gallina", unit_price="20.00", quantity=1
        )
        self.printed_job = PrintJob.objects.create(
            order=self.order,
            ticket_type=PrintJob.TicketType.NEW_ORDER,
            status=PrintJob.Status.PRINTED,
            printed_at=timezone.now(),
            last_item_id=self.first_item.id,
        )

    def test_addition_ticket_lists_only_items_added_since_last_print(self):
        addition = OrderItem.objects.create(
            order=self.order, name="Jugo de naranja", unit_price="5.00", quantity=1
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.ADDITION
        )
        text = build_ticket_text(job)
        self.assertIn("1x Jugo de naranja", text)
        self.assertNotIn("Sancocho de gallina", text)

    def test_void_ticket_lists_only_the_item_voided_since_last_print_with_reason(self):
        self.first_item.is_voided = True
        self.first_item.void_reason = "cliente cambio de pedido"
        self.first_item.save(update_fields=["is_voided", "void_reason"])
        OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.ITEM_VOIDED,
            performed_by=self.waiter,
            reason="cliente cambio de pedido",
            item=self.first_item,
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.VOID
        )
        text = build_ticket_text(job)
        self.assertIn("1x Sancocho de gallina", text)
        self.assertIn("Motivo: cliente cambio de pedido", text)

    def test_mixed_consolidation_shows_both_sections_under_one_header(self):
        addition = OrderItem.objects.create(
            order=self.order, name="Jugo de naranja", unit_price="5.00", quantity=1
        )
        self.first_item.is_voided = True
        self.first_item.void_reason = "ya no quiere"
        self.first_item.save(update_fields=["is_voided", "void_reason"])
        OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.ITEM_VOIDED,
            performed_by=self.waiter,
            reason="ya no quiere",
            item=self.first_item,
        )
        # the pending ticket started as an ADDITION and later absorbed a void
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.ADDITION
        )
        text = build_ticket_text(job)
        self.assertIn("ADICION - MESA 5", text)  # header stays fixed (RF-8)
        self.assertIn("1x Jugo de naranja", text)
        self.assertIn("1x Sancocho de gallina", text)
        self.assertIn("Motivo: ya no quiere", text)


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class OmitItemsVoidedBeforeFirstPrintTests(TestCase):
    """T14 — an item added and voided while still in the same pending
    (never-printed) ticket must not appear anywhere — not as "agregado",
    not as "anulado" (RF-8)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="cgarcia5", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=5, waiter=self.waiter)
        self.first_item = OrderItem.objects.create(
            order=self.order, name="Sancocho de gallina", unit_price="20.00", quantity=1
        )
        self.printed_job = PrintJob.objects.create(
            order=self.order,
            ticket_type=PrintJob.TicketType.NEW_ORDER,
            status=PrintJob.Status.PRINTED,
            printed_at=timezone.now(),
            last_item_id=self.first_item.id,
        )

    def test_item_added_and_voided_before_ever_printing_is_fully_omitted(self):
        fleeting = OrderItem.objects.create(
            order=self.order, name="Jugo de naranja", unit_price="5.00", quantity=1
        )
        fleeting.is_voided = True
        fleeting.void_reason = "me equivoque"
        fleeting.save(update_fields=["is_voided", "void_reason"])
        OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.ITEM_VOIDED,
            performed_by=self.waiter,
            reason="me equivoque",
            item=fleeting,
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.ADDITION
        )
        text = build_ticket_text(job)
        self.assertNotIn("Jugo de naranja", text)

    def test_item_that_was_already_printed_still_shows_as_voided(self):
        self.first_item.is_voided = True
        self.first_item.void_reason = "cliente cambio de pedido"
        self.first_item.save(update_fields=["is_voided", "void_reason"])
        OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.ITEM_VOIDED,
            performed_by=self.waiter,
            reason="cliente cambio de pedido",
            item=self.first_item,
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.VOID
        )
        text = build_ticket_text(job)
        self.assertIn("1x Sancocho de gallina", text)
        self.assertIn("Motivo: cliente cambio de pedido", text)


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class BuildNotesBlockTests(TestCase):
    """T11 — notes block, grouped at the top with the *** NOTA *** marker
    (RF-6)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="cgarcia2", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=5, waiter=self.waiter)

    def test_returns_empty_when_no_item_has_a_note(self):
        item = OrderItem.objects.create(
            order=self.order, name="Limonada natural", unit_price="4.50", quantity=1
        )
        self.assertEqual(build_notes_block([item]), [])

    def test_one_item_with_a_note(self):
        item = OrderItem.objects.create(
            order=self.order,
            name="Limonada natural",
            unit_price="4.50",
            quantity=1,
            note="sin azucar",
        )
        lines = build_notes_block([item])
        block = "\n".join(lines)
        self.assertIn("*** NOTA (LIMONADA NATURAL):", block)
        self.assertIn("SIN AZUCAR", block)
        self.assertTrue(block.rstrip().endswith("***"))
        # continuation lines (if the marker had to wrap) keep the hanging indent
        for line in lines[1:]:
            self.assertTrue(line.startswith("    "))

    def test_one_marker_per_item_with_a_note_others_are_skipped(self):
        with_note = OrderItem.objects.create(
            order=self.order,
            name="Limonada natural",
            unit_price="4.50",
            quantity=1,
            note="sin azucar",
        )
        without_note = OrderItem.objects.create(
            order=self.order, name="Sancocho", unit_price="20.00", quantity=1
        )
        block = "\n".join(build_notes_block([with_note, without_note]))
        self.assertEqual(block.count("*** NOTA"), 1)

    def test_no_line_exceeds_the_configured_width(self):
        item = OrderItem.objects.create(
            order=self.order,
            name="Postre de la casa",
            unit_price="6.00",
            quantity=1,
            note="una nota bastante larga que no cabe en una sola linea del ticket",
        )
        for line in build_notes_block([item]):
            self.assertLessEqual(len(line), 40)


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class FormatItemLineTests(TestCase):
    """T10 — line wrapping with hanging indent for long item names (RF-7)."""

    def test_short_name_fits_on_a_single_line(self):
        lines = format_item_line(2, "Limonada natural")
        self.assertEqual(lines, ["2x Limonada natural"])

    def test_long_name_wraps_with_a_hanging_indent(self):
        lines = format_item_line(
            1, "Arroz con pollo gigante especial de la casa para compartir"
        )
        self.assertGreater(len(lines), 1)
        self.assertTrue(lines[0].startswith("1x "))
        prefix_width = len("1x ")
        for continuation in lines[1:]:
            self.assertTrue(continuation.startswith(" " * prefix_width))
            self.assertFalse(continuation.startswith(" " * (prefix_width + 1)))

    def test_no_line_exceeds_the_configured_width(self):
        lines = format_item_line(
            1, "Arroz con pollo gigante especial de la casa para compartir"
        )
        for line in lines:
            self.assertLessEqual(len(line), 40)

    def test_never_splits_a_word_in_the_middle(self):
        lines = format_item_line(
            1, "Arroz con pollo gigante especial de la casa para compartir"
        )
        joined = " ".join(line.strip() for line in lines)
        self.assertEqual(
            joined,
            "1x Arroz con pollo gigante especial de la casa para compartir",
        )
