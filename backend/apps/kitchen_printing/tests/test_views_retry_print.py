from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


def _patched_adapter(adapter):
    return patch(
        "apps.kitchen_printing.services.get_printer_adapter", return_value=adapter
    )


class RetryPrintViewTests(TestCase):
    """T22, T25, T27 — POST /api/pedidos/{id}/reimprimir (RF-9, RF-10,
    RF-11)."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="retry_w", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="retry_w2", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
            services.send_order(self.order)

    def test_owner_retries_successfully(self):
        self.client.force_authenticate(self.waiter)
        with _patched_adapter(FakePrinterAdapter()):
            response = self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["print_warning"])
        self.assertEqual(response.data["id"], self.order.id)
        self.assertFalse(response.data["has_pending_print"])

    def test_owner_retries_and_fails_again(self):
        self.client.force_authenticate(self.waiter)
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            response = self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["print_warning"])

    def test_non_owner_gets_403(self):
        self.client.force_authenticate(self.other_waiter)
        response = self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_order_gets_404(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.post("/api/pedidos/9999/reimprimir")
        self.assertEqual(response.status_code, 404)

    def test_no_pending_ticket_gets_404(self):
        self.client.force_authenticate(self.waiter)
        with _patched_adapter(FakePrinterAdapter()):
            self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        response = self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        self.assertEqual(response.status_code, 404)

    def test_charged_order_gets_409(self):
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.waiter)
        response = self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        self.assertEqual(response.status_code, 409)

    def test_unauthenticated_gets_401(self):
        response = self.client.post(f"/api/pedidos/{self.order.id}/reimprimir")
        self.assertEqual(response.status_code, 401)
