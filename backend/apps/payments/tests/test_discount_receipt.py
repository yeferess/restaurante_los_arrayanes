from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.orders.models import Order, OrderItem, Table
from apps.payments import services
from apps.payments.models import Payment, PaymentAccount
from apps.payments.receipt import build_receipt_text, format_pesos

User = get_user_model()


class _OrderFixture:
    def _setup_order(self):
        self.waiter = User.objects.create_user(
            username="mesero_disc", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_disc", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        Table.objects.create(number=5, status=Table.Status.OCCUPIED)
        self.account = PaymentAccount.objects.get(name="Efectivo")
        self.order = Order.objects.create(
            table_number=5,
            waiter=self.waiter,
            status=Order.Status.IN_PROGRESS,
            daily_number=12,
            admin_note="pago pendiente de revisar",
        )
        OrderItem.objects.create(
            order=self.order,
            name="Bandeja paisa",
            unit_price="25000.00",
            quantity=2,
            note="sin cebolla",
        )
        OrderItem.objects.create(
            order=self.order, name="Jugo de mora", unit_price="5000.00", quantity=1
        )
        OrderItem.objects.create(
            order=self.order,
            name="Gaseosa",
            unit_price="4000.00",
            quantity=1,
            is_voided=True,
        )


class ComputeChargeTests(_OrderFixture, TestCase):
    """005 RF-10 — discount in pesos, validated in a single place."""

    def setUp(self):
        self._setup_order()

    def test_without_discount_total_is_the_subtotal(self):
        amounts = services.compute_charge(self.order)
        self.assertEqual(amounts["subtotal"], Decimal("55000.00"))
        self.assertEqual(amounts["discount"], Decimal("0"))
        self.assertEqual(amounts["total"], Decimal("55000.00"))

    def test_discount_is_subtracted(self):
        amounts = services.compute_charge(self.order, "5000")
        self.assertEqual(amounts["total"], Decimal("50000.00"))

    def test_discount_equal_to_subtotal_is_allowed(self):
        self.assertEqual(services.compute_charge(self.order, "55000")["total"], 0)

    def test_rejects_negative_greater_or_non_numeric_discounts(self):
        for raw in ("-1", "55000.01", "abc", "NaN"):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                services.compute_charge(self.order, raw)


class ChargeWithDiscountTests(_OrderFixture, TestCase):
    """005 RF-3, RF-10 — the payment stores subtotal, discount and the
    amount actually paid."""

    def setUp(self):
        self._setup_order()

    def test_stores_subtotal_discount_reason_and_net_amount(self):
        payment = services.charge_order(
            self.order,
            self.admin,
            self.account,
            discount="5000",
            discount_reason="  cliente frecuente  ",
        )
        self.assertEqual(payment.subtotal, Decimal("55000.00"))
        self.assertEqual(payment.discount, Decimal("5000"))
        self.assertEqual(payment.amount, Decimal("50000.00"))
        self.assertEqual(payment.discount_reason, "cliente frecuente")
        self.assertEqual(payment.charged_by, self.admin)

    def test_reason_is_optional(self):
        payment = services.charge_order(
            self.order, self.admin, self.account, discount="5000"
        )
        self.assertEqual(payment.discount_reason, "")

    def test_without_discount_amount_equals_subtotal_and_reason_is_dropped(self):
        payment = services.charge_order(
            self.order, self.admin, self.account, discount_reason="ignorado"
        )
        self.assertEqual(payment.amount, payment.subtotal)
        self.assertEqual(payment.discount, 0)
        self.assertEqual(payment.discount_reason, "")

    def test_invalid_discount_charges_nothing(self):
        with self.assertRaises(ValidationError):
            services.charge_order(
                self.order, self.admin, self.account, discount="99999"
            )
        self.assertFalse(Payment.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.IN_PROGRESS)


class ReceiptRenderingTests(_OrderFixture, TestCase):
    """005 RF-11 — the customer receipt's text."""

    def setUp(self):
        self._setup_order()

    def test_format_pesos(self):
        self.assertEqual(format_pesos(Decimal("50000.00")), "50.000")
        self.assertEqual(format_pesos(Decimal("1234.50")), "1.234,50")

    def test_receipt_with_discount(self):
        payment = services.charge_order(
            self.order, self.admin, self.account, discount="5000"
        )
        text = build_receipt_text(self.order, payment)
        lines = text.splitlines()
        self.assertEqual(lines[0].strip(), "FINCA DE RECREO LOS ARRAYANES")
        self.assertEqual(lines[1].strip(), "COMPROBANTE")
        self.assertIn("N° 12  Mesa 5", text)
        self.assertIn("2x Bandeja paisa", text)
        self.assertRegex(text, r"2 x 25\.000 +50\.000")
        self.assertRegex(text, r"Subtotal +55\.000")
        self.assertRegex(text, r"Descuento +-5\.000")
        self.assertRegex(text, r"TOTAL +50\.000")
        self.assertIn("Forma de pago: Efectivo", text)
        self.assertNotIn("Gaseosa", text)
        self.assertNotIn("sin cebolla", text)
        self.assertNotIn("revisar", text)
        self.assertTrue(all(len(line) <= 40 for line in lines))

    def test_receipt_without_discount_omits_subtotal_and_discount(self):
        payment = services.charge_order(self.order, self.admin, self.account)
        text = build_receipt_text(self.order, payment)
        self.assertNotIn("Descuento", text)
        self.assertNotIn("Subtotal", text)
        self.assertRegex(text, r"TOTAL +55\.000")


class PrintReceiptServiceTests(_OrderFixture, TestCase):
    """005 RF-11 — printing reuses the kitchen printer and lock."""

    def setUp(self):
        self._setup_order()

    def test_rejects_an_order_that_is_not_charged(self):
        with self.assertRaises(ValidationError):
            services.print_receipt(self.order)

    def test_prints_the_receipt_text(self):
        services.charge_order(self.order, self.admin, self.account)
        adapter = FakePrinterAdapter()
        with mock.patch(
            "apps.payments.services.get_printer_adapter", return_value=adapter
        ):
            warning = services.print_receipt(self.order)
        self.assertIsNone(warning)
        self.assertEqual(adapter.call_count, 1)
        self.assertIn("COMPROBANTE", adapter.printed_texts[0])

    def test_returns_a_warning_when_the_printer_is_missing(self):
        services.charge_order(self.order, self.admin, self.account)
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with mock.patch(
            "apps.payments.services.get_printer_adapter", return_value=adapter
        ):
            warning = services.print_receipt(self.order)
        self.assertEqual(warning, "Impresora de cocina no detectada.")


class DiscountAndReceiptViewTests(_OrderFixture, APITestCase):
    """005 RF-10, RF-11 — charge with discount, preview and receipt
    endpoints."""

    def setUp(self):
        self._setup_order()

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_disc", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_disc", "pin": "1234"}
        )

    def test_charge_with_discount(self):
        self._login_admin()
        response = self.client.post(
            f"/api/pedidos/{self.order.id}/cobrar",
            {
                "account_id": self.account.id,
                "discount": "5000",
                "discount_reason": "demora",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = response.data["active_payment"]
        self.assertEqual(Decimal(payment["subtotal"]), Decimal("55000"))
        self.assertEqual(Decimal(payment["discount"]), Decimal("5000"))
        self.assertEqual(Decimal(payment["amount"]), Decimal("50000"))
        self.assertEqual(payment["discount_reason"], "demora")
        self.assertEqual(response.data["admin_note"], "pago pendiente de revisar")

    def test_charge_with_invalid_discount_returns_400(self):
        self._login_admin()
        response = self.client.post(
            f"/api/pedidos/{self.order.id}/cobrar",
            {"account_id": self.account.id, "discount": "-3"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview(self):
        self._login_admin()
        url = f"/api/pedidos/{self.order.id}/cobro/previsualizar"
        response = self.client.post(url, {"discount": "5000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("55000"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("50000"))
        self.assertEqual(
            self.client.post(url, {"discount": "60000"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(Payment.objects.exists())

    def test_preview_of_a_non_chargeable_order_returns_409(self):
        self.order.status = Order.Status.DRAFT
        self.order.save()
        self._login_admin()
        response = self.client.post(
            f"/api/pedidos/{self.order.id}/cobro/previsualizar"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_receipt_endpoint(self):
        self._login_admin()
        url = f"/api/pedidos/{self.order.id}/comprobante"
        self.assertEqual(self.client.post(url).status_code, status.HTTP_409_CONFLICT)
        services.charge_order(self.order, self.admin, self.account)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["print_warning"])

    def test_unknown_order_returns_404(self):
        self._login_admin()
        for url in (
            "/api/pedidos/999999/comprobante",
            "/api/pedidos/999999/cobro/previsualizar",
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.post(url).status_code, status.HTTP_404_NOT_FOUND
                )

    def test_mesero_gets_403(self):
        self._login_mesero()
        for url in (
            f"/api/pedidos/{self.order.id}/comprobante",
            f"/api/pedidos/{self.order.id}/cobro/previsualizar",
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.post(url).status_code, status.HTTP_403_FORBIDDEN
                )
