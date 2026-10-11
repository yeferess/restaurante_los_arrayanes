from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from django.utils import timezone

from apps.kitchen_printing.models import PrintJob
from apps.kitchen_printing.rendering import (
    build_ticket_text,
    format_item_line,
    format_note_lines,
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

    def test_includes_daily_number_and_waiter_username(self):
        """T37 — the header shows the daily number (003-RF-14), never
        the internal id."""
        self.order.daily_number = 7
        self.order.sent_at = timezone.now()
        self.order.save(update_fields=["daily_number", "sent_at"])
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        self.assertIn("N° 7", text)
        self.assertIn("Mesero: cgarcia", text)
        self.assertNotIn(f"Pedido #{self.order.id}", text)
        self.assertNotIn(f"#{self.order.id}", text)

    def test_blank_daily_number_for_a_pre_upgrade_order(self):
        """T38 — an order with no daily_number (sent before 003-RF-14
        existed) still prints, with that field blank."""
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        self.assertIn("N°", text)
        self.assertNotIn("N° None", text)

    def test_sent_at_and_print_attempt_time_are_two_distinct_fields(self):
        """T39 — the order's send time (003-RF-14) and the print
        attempt's own time (already existing, RF-2) never get mixed up
        on the same ticket."""
        self.order.daily_number = 3
        self.order.sent_at = timezone.now() - timezone.timedelta(hours=1)
        self.order.save(update_fields=["daily_number", "sent_at"])
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        text = build_ticket_text(job)
        sent_label = timezone.localtime(self.order.sent_at).strftime("%d/%m %H:%M")
        printed_label = timezone.localtime().strftime("%d/%m %H:%M")
        self.assertIn(f"Enviado {sent_label}", text)
        self.assertIn(f"Impreso {printed_label}", text)
        self.assertNotEqual(sent_label, printed_label)

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

    def test_note_appears_right_under_its_own_item(self):
        OrderItem.objects.create(
            order=self.order,
            name="Limonada natural",
            unit_price="4.50",
            quantity=1,
            note="sin azucar",
        )
        OrderItem.objects.create(
            order=self.order, name="Sancocho", unit_price="20.00", quantity=1
        )
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        lines = build_ticket_text(job).split("\n")
        item_index = lines.index("1x Limonada natural")
        self.assertEqual(lines[item_index + 1], "   *** NOTA: SIN AZUCAR ***")
        self.assertEqual(lines[item_index + 2], "1x Sancocho")
        self.assertEqual(sum("*** NOTA" in line for line in lines), 1)


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
class FormatNoteLinesTests(TestCase):
    """T11 — an item's note, right under its own line with the
    *** NOTA *** marker (RF-6)."""

    def test_returns_empty_when_the_item_has_no_note(self):
        self.assertEqual(format_note_lines(1, ""), [])

    def test_short_note_is_one_marker_line_aligned_with_the_item_name(self):
        self.assertEqual(format_note_lines(3, "sin cebolla"), ["   *** NOTA: SIN CEBOLLA ***"])

    def test_indent_follows_the_width_of_the_quantity(self):
        self.assertEqual(format_note_lines(12, "sin sal"), ["    *** NOTA: SIN SAL ***"])

    def test_strips_accents(self):
        self.assertEqual(format_note_lines(1, "sin azúcar"), ["   *** NOTA: SIN AZUCAR ***"])

    def test_long_note_wraps_keeping_the_indent_and_the_width(self):
        lines = format_note_lines(
            1, "una nota bastante larga que no cabe en una sola linea del ticket"
        )
        self.assertGreater(len(lines), 1)
        self.assertTrue(lines[-1].endswith("***"))
        for line in lines:
            self.assertTrue(line.startswith("   "))
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
