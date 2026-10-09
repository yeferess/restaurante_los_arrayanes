from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.kitchen_printing import services as kitchen_services
from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.models import PrintJob
from apps.kitchen_printing.rendering import build_ticket_text
from apps.orders import services

User = get_user_model()


def _patched_adapter(adapter):
    return patch(
        "apps.kitchen_printing.services.get_printer_adapter", return_value=adapter
    )


class FullConsolidationFlowTests(TestCase):
    """T29 — a failed "PEDIDO NUEVO" ticket absorbs a later addition and
    a later void of that same addition (never printed in between), then
    a successful retry opens the door for the next event to start a
    fresh, independent ticket (RF-8)."""

    def test_consolidation_then_retry_then_next_event_opens_a_new_job(self):
        services.resize_tables(1)
        waiter = User.objects.create_user(
            username="t29_w", password="1234", role=User.Role.MESERO
        )
        order = services.create_order(waiter, table_number=1)
        services.add_item(order, name="Sancocho de gallina", price=Decimal("20.00"))

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            services.send_order(order)

        self.assertEqual(PrintJob.objects.filter(order=order).count(), 1)
        job = PrintJob.objects.get(order=order)
        self.assertEqual(job.status, PrintJob.Status.PENDING)
        self.assertEqual(job.ticket_type, PrintJob.TicketType.NEW_ORDER)

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            addition = services.add_item(
                order, name="Jugo de naranja", price=Decimal("5.00")
            )

        # still the same single pending job — consolidated, not a 2nd one
        self.assertEqual(PrintJob.objects.filter(order=order).count(), 1)
        job.refresh_from_db()
        self.assertEqual(job.ticket_type, PrintJob.TicketType.NEW_ORDER)

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            services.void_item(order, addition, waiter, "cliente ya no lo quiere")

        # the voided addition never reached paper — omitted entirely
        text = build_ticket_text(job)
        self.assertIn("Sancocho de gallina", text)
        self.assertNotIn("Jugo de naranja", text)

        with _patched_adapter(FakePrinterAdapter()):
            warning = kitchen_services.retry_print(order, waiter)
        self.assertIsNone(warning)
        job.refresh_from_db()
        self.assertEqual(job.status, PrintJob.Status.PRINTED)

        # the next event opens an independent, new PrintJob
        with _patched_adapter(FakePrinterAdapter()):
            services.add_item(order, name="Postre de la casa", price=Decimal("6.00"))
        self.assertEqual(PrintJob.objects.filter(order=order).count(), 2)
