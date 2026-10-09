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
    """T23 — enviar/agregar ítem/anular ítem expose print_warning without
    changing their usual success status code (RF-9)."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="pw_w", password="1234", role=User.Role.MESERO
        )
        self.client.force_authenticate(self.waiter)
        self.order = services.create_order(self.waiter, table_number=1)

    def test_send_order_reports_a_print_warning_on_failure(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            response = self.client.post(f"/api/pedidos/{self.order.id}/enviar")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["print_warning"])

    def test_send_order_reports_no_warning_on_success(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        with _patched_adapter(FakePrinterAdapter()):
            response = self.client.post(f"/api/pedidos/{self.order.id}/enviar")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["print_warning"])

    def test_add_item_reports_print_warning_only_once_sent(self):
        with _patched_adapter(FakePrinterAdapter()):
            response = self.client.post(
                f"/api/pedidos/{self.order.id}/items",
                {"name": "Limonada", "price": "4.50", "quantity": 1},
            )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["print_warning"])

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            self.client.post(f"/api/pedidos/{self.order.id}/enviar")
            response = self.client.post(
                f"/api/pedidos/{self.order.id}/items",
                {"name": "Jugo", "price": "5.00", "quantity": 1},
            )
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.data["print_warning"])

    def test_void_item_reports_print_warning(self):
        with _patched_adapter(FakePrinterAdapter()):
            item1 = services.add_item(
                self.order, name="Limonada", price=Decimal("4.50")
            )
            services.add_item(self.order, name="Jugo", price=Decimal("5.00"))
            services.send_order(self.order)

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            response = self.client.post(
                f"/api/pedidos/{self.order.id}/items/{item1.id}/anular",
                {"reason": "cliente se arrepintio"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["print_warning"])
