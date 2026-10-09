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


class HasPendingPrintTests(TestCase):
    """T24 — has_pending_print on pedidos/mios, pedidos/entrantes y
    pedidos/{id} (RF-10)."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="hpp_w", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="hpp_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))

    def test_my_orders_reports_true_after_a_failed_print(self):
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            services.send_order(self.order)
        self.client.force_authenticate(self.waiter)
        response = self.client.get("/api/pedidos/mios")
        self.assertTrue(response.data[0]["has_pending_print"])

    def test_my_orders_reports_false_after_a_successful_print(self):
        with _patched_adapter(FakePrinterAdapter()):
            services.send_order(self.order)
        self.client.force_authenticate(self.waiter)
        response = self.client.get("/api/pedidos/mios")
        self.assertFalse(response.data[0]["has_pending_print"])

    def test_incoming_orders_reports_true_after_a_failed_print(self):
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            services.send_order(self.order)
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/pedidos/entrantes")
        self.assertTrue(response.data[0]["has_pending_print"])

    def test_order_detail_reports_has_pending_print(self):
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            services.send_order(self.order)
        self.client.force_authenticate(self.waiter)
        response = self.client.get(f"/api/pedidos/{self.order.id}")
        self.assertTrue(response.data["has_pending_print"])
