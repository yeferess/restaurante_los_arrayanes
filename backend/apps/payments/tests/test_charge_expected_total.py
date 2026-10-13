from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services as order_services
from apps.orders.models import Order, OrderItem
from apps.payments import services
from apps.payments.models import Payment
from apps.payments.tests.test_discount_receipt import _OrderFixture


class ChargeExpectedTotalServiceTests(_OrderFixture, TestCase):
    """005 RF-12 — the charge is refused when the order changed after the
    admin opened the charge window (the active subtotal here is 55.000)."""

    def setUp(self):
        self._setup_order()

    def test_charges_when_the_expected_total_matches(self):
        payment = services.charge_order(
            self.order, self.admin, self.account, expected_total="55000.00"
        )
        self.assertEqual(payment.amount, Decimal("55000.00"))

    def test_matching_total_with_a_discount_charges_the_net(self):
        payment = services.charge_order(
            self.order, self.admin, self.account, discount="5000", expected_total="55000"
        )
        self.assertEqual(payment.amount, Decimal("50000.00"))

    def test_an_addition_after_opening_the_window_refuses_the_charge(self):
        # El admin vio 55.000; el mesero agrega un ítem antes de que cobre.
        order_services.add_item(self.order, name="Churrasco", price=Decimal("32000"))
        order_services.send_additions(self.order, self.order.waiter)
        with self.assertRaises(ValidationError) as ctx:
            services.charge_order(
                self.order, self.admin, self.account, expected_total="55000.00"
            )
        self.assertEqual(ctx.exception.code, "order_changed")
        self.assertFalse(Payment.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.IN_PROGRESS)

    def test_a_voided_item_after_opening_the_window_refuses_the_charge(self):
        item = OrderItem.objects.get(order=self.order, name="Jugo de mora")
        item.is_voided = True
        item.save()
        with self.assertRaises(ValidationError) as ctx:
            services.charge_order(
                self.order, self.admin, self.account, expected_total="55000.00"
            )
        self.assertEqual(ctx.exception.code, "order_changed")

    def test_without_expected_total_the_charge_still_works(self):
        payment = services.charge_order(self.order, self.admin, self.account)
        self.assertEqual(payment.amount, Decimal("55000.00"))

    def test_a_non_numeric_expected_total_is_invalid(self):
        with self.assertRaises(ValidationError) as ctx:
            services.charge_order(
                self.order, self.admin, self.account, expected_total="abc"
            )
        self.assertEqual(ctx.exception.code, "invalid")


class ChargeExpectedTotalViewTests(_OrderFixture, APITestCase):
    """005 RF-12 — POST /api/pedidos/{id}/cobrar with `expected_total`."""

    def setUp(self):
        self._setup_order()
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_disc", "password": "Sup3rSecreta"},
        )

    def _charge(self, expected_total):
        return self.client.post(
            f"/api/pedidos/{self.order.id}/cobrar",
            {"account_id": self.account.id, "expected_total": expected_total},
            format="json",
        )

    def test_matching_total_returns_200(self):
        response = self._charge("55000.00")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["active_payment"]["amount"], "55000.00")

    def test_stale_total_returns_409_with_the_message(self):
        order_services.add_item(self.order, name="Churrasco", price=Decimal("32000"))
        order_services.send_additions(self.order, self.order.waiter)
        response = self._charge("55000.00")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("El pedido cambió", response.data["detail"][0])
        self.assertFalse(Payment.objects.exists())

    def test_invalid_total_returns_400(self):
        response = self._charge("abc")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
