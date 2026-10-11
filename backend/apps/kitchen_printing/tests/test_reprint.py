from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.models import PrintJob
from apps.kitchen_printing.rendering import _since_reference, build_reprint_text
from apps.orders import services
from apps.orders.models import Order
from apps.payments.models import PaymentAccount
from apps.payments.services import charge_order

User = get_user_model()


def _patched_adapter(adapter):
    return patch(
        "apps.kitchen_printing.services.get_printer_adapter", return_value=adapter
    )


@override_settings(KITCHEN_PRINTER_COLUMNS=40)
class ReprintOrderTests(TestCase):
    """RF-12 — manual reprint of the whole order."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="rp_w", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="rp_w2", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="rp_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        with _patched_adapter(FakePrinterAdapter()):
            services.add_item(
                self.order, name="Bandeja paisa", price=Decimal("25.00"), quantity=3,
                note="sin cebolla",
            )
            voided = services.add_item(
                self.order, name="Jugo de mora", price=Decimal("5.00")
            )
            services.send_order(self.order)
            services.void_item(self.order, voided, self.waiter, "se equivoco")

    def _reprint(self, user, adapter=None):
        self.client.force_authenticate(user)
        with _patched_adapter(adapter or FakePrinterAdapter()):
            return self.client.post(f"/api/pedidos/{self.order.id}/reimpresion")

    def _charge(self):
        charge_order(self.order, self.admin, PaymentAccount.objects.get(name="Efectivo"))
        self.order.refresh_from_db()

    def test_text_has_the_reprint_header_and_every_active_item_with_its_note(self):
        lines = build_reprint_text(self.order).split("\n")
        self.assertIn("REIMPRESION - MESA 1", "\n".join(lines))
        index = lines.index("3x Bandeja paisa")
        self.assertEqual(lines[index + 1], "   *** NOTA: SIN CEBOLLA ***")
        self.assertNotIn("Jugo de mora", "\n".join(lines))

    def test_owner_reprints_an_open_order(self):
        adapter = FakePrinterAdapter()
        response = self._reprint(self.waiter, adapter)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["print_warning"])
        self.assertIn("REIMPRESION", adapter.printed_texts[0])
        job = PrintJob.objects.get(order=self.order, ticket_type=PrintJob.TicketType.REPRINT)
        self.assertEqual(job.status, PrintJob.Status.PRINTED)

    def test_admin_reprints_an_open_order(self):
        self.assertEqual(self._reprint(self.admin).status_code, 200)

    def test_admin_reprints_a_charged_order(self):
        self._charge()
        self.assertEqual(self._reprint(self.admin).status_code, 200)

    def test_owner_cannot_reprint_a_charged_order(self):
        self._charge()
        self.assertEqual(self._reprint(self.waiter).status_code, 409)

    def test_other_waiter_gets_403(self):
        self.assertEqual(self._reprint(self.other_waiter).status_code, 403)

    def test_draft_order_gets_409(self):
        draft = Order.objects.create(table_number=1, waiter=self.waiter)
        self.client.force_authenticate(self.waiter)
        response = self.client.post(f"/api/pedidos/{draft.id}/reimpresion")
        self.assertEqual(response.status_code, 409)

    def test_nonexistent_order_gets_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/pedidos/9999/reimpresion")
        self.assertEqual(response.status_code, 404)

    def test_requires_a_session(self):
        response = APIClient().post(f"/api/pedidos/{self.order.id}/reimpresion")
        self.assertIn(response.status_code, (401, 403))

    def test_failed_reprint_returns_the_warning_and_records_nothing(self):
        response = self._reprint(
            self.waiter, FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["print_warning"])
        self.assertFalse(response.data["has_pending_print"])
        self.assertFalse(
            PrintJob.objects.filter(
                order=self.order, ticket_type=PrintJob.TicketType.REPRINT
            ).exists()
        )

    def test_reprint_does_not_move_the_already_printed_reference(self):
        before = _since_reference(self.order)
        self._reprint(self.waiter)
        self.assertEqual(_since_reference(self.order), before)
