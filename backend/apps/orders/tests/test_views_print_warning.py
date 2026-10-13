from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.orders import services

User = get_user_model()


def _patched_adapter(adapter):
    return patch(
        "apps.kitchen_printing.services.get_printer_adapter", return_value=adapter
    )


class PrintWarningInResponsesTests(TestCase):
    """T23 — print_warning (RF-9). Only "Imprimir pedido" ever reaches the
    printer (RF-1): crear/agregar/anular never carry a warning, even with
    the printer down, and keep their usual success status code."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="pw_w", password="1234", role=User.Role.MESERO
        )
        self.client.force_authenticate(self.waiter)
        self.order = services.create_order(self.waiter, table_number=1)

    def test_creating_the_order_never_reports_a_print_warning(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            response = self.client.post(f"/api/pedidos/{self.order.id}/enviar")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["print_warning"])
        self.assertEqual(adapter.printed_texts, [])

    def test_adding_and_voiding_never_report_a_print_warning(self):
        item1 = services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.add_item(self.order, name="Jugo", price=Decimal("5.00"))
        services.send_order(self.order)

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            added = self.client.post(
                f"/api/pedidos/{self.order.id}/items",
                {"name": "Te", "price": "3.00", "quantity": 1},
            )
            voided = self.client.post(
                f"/api/pedidos/{self.order.id}/items/{item1.id}/anular",
                {"reason": "cliente se arrepintio"},
            )
        self.assertEqual(added.status_code, 201)
        self.assertIsNone(added.data["print_warning"])
        self.assertEqual(voided.status_code, 200)
        self.assertIsNone(voided.data["print_warning"])

    def test_print_reports_the_warning_on_failure(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            response = self.client.post(f"/api/pedidos/{self.order.id}/imprimir")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["print_warning"])
        self.assertTrue(response.data["has_pending_print"])

    def test_print_reports_no_warning_on_success(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        with _patched_adapter(FakePrinterAdapter()):
            response = self.client.post(f"/api/pedidos/{self.order.id}/imprimir")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["print_warning"])
        self.assertFalse(response.data["has_unprinted_changes"])
