"""T39 — 005 RF-13: the bill printed from the charge window before
paying — same items, prices and discount as the charge, and it charges
nothing."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.kitchen_printing.adapters import PrinterFailureError, PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.orders.models import Order, OrderItem, Table
from apps.payments import services
from apps.payments.models import Payment, PaymentAccount
from apps.payments.receipt import build_bill_text

User = get_user_model()


class _Fixture(TestCase):
    def setUp(self):
        self.waiter = User.objects.create_user(
            username="waiter_bill", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_bill", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        Table.objects.create(number=3, status=Table.Status.OCCUPIED)
        self.order = Order.objects.create(
            table_number=3,
            waiter=self.waiter,
            status=Order.Status.IN_PROGRESS,
            daily_number=12,
            admin_note="cliente frecuente",
        )
        OrderItem.objects.create(
            order=self.order,
            name="Bandeja paisa",
            unit_price="25000.00",
            quantity=3,
            note="sin chorizo",
        )
        OrderItem.objects.create(
            order=self.order, name="Ajiaco", unit_price="20000.00", quantity=1
        )
        OrderItem.objects.create(
            order=self.order,
            name="Gaseosa",
            unit_price="4000.00",
            quantity=1,
            is_voided=True,
        )
        # An addition the waiter never sent: not part of the bill.
        OrderItem.objects.create(
            order=self.order,
            name="Postre",
            unit_price="8000.00",
            quantity=1,
            line_type=OrderItem.LineType.ADDITION,
        )
        self.printer = FakePrinterAdapter()
        patcher = mock.patch(
            "apps.payments.services.get_printer_adapter",
            side_effect=lambda: self.printer,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _text(self, discount=None):
        return build_bill_text(self.order, services.preview_charge(self.order, discount))


class BillTextTests(_Fixture):
    def test_bill_lists_items_with_prices_and_the_total(self):
        text = self._text()
        self.assertIn("CUENTA", text)
        self.assertIn("N° 12  Mesa 3", text)
        self.assertIn("3x Bandeja paisa", text)
        self.assertIn("75.000", text)
        self.assertIn("1x Ajiaco", text)
        self.assertRegex(text, r"TOTAL\s+95\.000")
        self.assertIn("No es comprobante de pago", text)

    def test_bill_leaves_out_payment_option_notes_voided_and_unsent(self):
        text = self._text()
        self.assertNotIn("COMPROBANTE", text)
        self.assertNotIn("Forma de pago", text)
        self.assertNotIn("sin chorizo", text.lower())
        self.assertNotIn("NOTA", text)
        self.assertNotIn("cliente frecuente", text)
        self.assertNotIn("Gaseosa", text)
        self.assertNotIn("Postre", text)

    def test_bill_without_discount_has_no_subtotal_line(self):
        text = self._text()
        self.assertNotIn("Subtotal", text)
        self.assertNotIn("Descuento", text)

    def test_bill_with_discount_shows_subtotal_discount_and_total(self):
        text = self._text("10000")
        self.assertRegex(text, r"Subtotal\s+95\.000")
        self.assertRegex(text, r"Descuento\s+-10\.000")
        self.assertRegex(text, r"TOTAL\s+85\.000")

    def test_counter_order_bill_says_mostrador(self):
        self.order.table_number = None
        self.order.save(update_fields=["table_number"])
        text = self._text()
        self.assertIn("Mostrador", text)
        self.assertNotIn("Mesa", text)


class PrintBillServiceTests(_Fixture):
    def test_prints_and_charges_nothing(self):
        warning = services.print_bill(self.order, "10000")
        self.assertIsNone(warning)
        self.assertEqual(len(self.printer.printed_texts), 1)
        self.assertIn("TOTAL", self.printer.printed_texts[0])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.IN_PROGRESS)
        self.assertFalse(Payment.objects.filter(order=self.order).exists())
        self.assertEqual(Table.objects.get(number=3).status, Table.Status.OCCUPIED)

    def test_rejects_an_order_not_in_progress(self):
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.print_bill(self.order)
        self.assertEqual(self.printer.printed_texts, [])

    def test_rejects_a_discount_above_the_total(self):
        with self.assertRaises(ValidationError):
            services.print_bill(self.order, "100000")

    def test_returns_the_printer_warning_when_it_fails(self):
        self.printer = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        self.assertEqual(
            services.print_bill(self.order), services.PRINTER_NOT_DETECTED_MESSAGE
        )
        self.printer = FakePrinterAdapter(fail_with=PrinterFailureError)
        self.assertEqual(services.print_bill(self.order), services.PRINTER_FAILURE_MESSAGE)


class BillViewTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.url = f"/api/pedidos/{self.order.id}/cuenta"
        self.client = APIClient()

    def test_admin_prints_the_bill_with_the_discount(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {"discount": "10000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["print_warning"])
        self.assertRegex(self.printer.printed_texts[0], r"TOTAL\s+85\.000")

    def test_a_waiter_cannot_print_the_bill(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.printer.printed_texts, [])

    def test_a_charged_order_answers_409(self):
        account = PaymentAccount.objects.get(name="Efectivo")
        services.charge_order(self.order, self.admin, account)
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_an_invalid_discount_answers_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {"discount": "100000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_order_answers_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/pedidos/99999/cuenta", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
