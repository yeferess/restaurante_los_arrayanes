"""T98 — 003 RF-18: el admin crea pedidos desde el computador, en una
mesa o de mostrador (sin mesa), y los maneja como dueño.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.orders import services
from apps.orders.models import Order, Table
from apps.payments.models import Payment, PaymentAccount
from apps.payments.receipt import build_receipt_text
from apps.payments.services import charge_order, void_charge

User = get_user_model()


class _Fixture(TestCase):
    def setUp(self):
        services.resize_tables(2)
        self.admin = User.objects.create_user(
            username="admin_caja", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="mesero_turno", password="1234", role=User.Role.MESERO
        )
        self.printer = FakePrinterAdapter()
        patcher = patch(
            "apps.kitchen_printing.services.get_printer_adapter",
            side_effect=lambda: self.printer,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        self.waiter_client = APIClient()
        self.waiter_client.force_authenticate(self.waiter)
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _create(self, client, table_number=None):
        body = {} if table_number is None else {"table_number": table_number}
        return client.post("/api/pedidos", body, format="json")

    def _build_counter_order(self):
        """El admin crea un pedido de mostrador con un ítem y lo crea."""
        order_id = self._create(self.admin_client).data["id"]
        self.admin_client.post(
            f"/api/pedidos/{order_id}/items",
            {"name": "Empanada", "price": "3000", "quantity": 2},
            format="json",
        )
        self.admin_client.post(f"/api/pedidos/{order_id}/enviar")
        return Order.objects.get(pk=order_id)


class AdminCreatesOrdersTests(_Fixture):
    def test_admin_creates_a_counter_order_without_a_table(self):
        response = self._create(self.admin_client)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["table_number"])
        self.assertEqual(response.data["waiter_username"], "admin_caja")
        # Ninguna mesa se ocupó.
        self.assertFalse(Table.objects.exclude(status=Table.Status.FREE).exists())

    def test_admin_creates_an_order_on_a_free_table(self):
        response = self._create(self.admin_client, table_number=2)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Table.objects.get(number=2).status, Table.Status.OCCUPIED)

    def test_a_waiter_still_must_choose_a_table(self):
        self.assertEqual(self._create(self.waiter_client).status_code, 400)
        with self.assertRaises(ValidationError):
            services.create_order(self.waiter, None)

    def test_admin_builds_creates_and_prints_their_counter_order(self):
        order = self._build_counter_order()
        self.assertEqual(order.status, Order.Status.IN_PROGRESS)
        self.assertIsNotNone(order.daily_number)

        response = self.admin_client.post(f"/api/pedidos/{order.id}/imprimir")
        self.assertEqual(response.status_code, 200)
        ticket = self.printer.printed_texts[0]
        self.assertIn("PEDIDO NUEVO - MOSTRADOR", ticket)
        self.assertIn("Mesero: admin_caja", ticket)
        self.assertIn("Empanada", ticket)

    def test_admin_sees_their_own_order_as_its_owner(self):
        order = self._build_counter_order()
        self.admin_client.post(
            f"/api/pedidos/{order.id}/items",
            {"name": "Gaseosa", "price": "4000"},
            format="json",
        )
        detail = self.admin_client.get(f"/api/pedidos/{order.id}").data
        self.assertEqual(detail["pending_additions_count"], 1)

        mine = self.admin_client.get("/api/pedidos/mios").data
        self.assertEqual([o["id"] for o in mine], [order.id])

    def test_the_counter_order_shows_up_in_incoming(self):
        order = self._build_counter_order()
        incoming = self.admin_client.get("/api/pedidos/entrantes").data
        self.assertEqual([o["id"] for o in incoming], [order.id])
        self.assertIsNone(incoming[0]["table_number"])

    def test_a_counter_order_has_no_table_to_correct(self):
        order = self._build_counter_order()
        response = self.admin_client.post(
            f"/api/pedidos/{order.id}/mesa", {"table_number": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class OwnershipTests(_Fixture):
    def test_a_waiter_cannot_touch_the_admins_order(self):
        order = self._build_counter_order()
        self.assertEqual(
            self.waiter_client.post(
                f"/api/pedidos/{order.id}/items",
                {"name": "Tinto", "price": "2000"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.waiter_client.post(f"/api/pedidos/{order.id}/imprimir").status_code, 403
        )
        self.assertEqual(self.waiter_client.get("/api/pedidos/mios").data, [])

    def test_the_admin_cannot_edit_a_waiters_order(self):
        order = services.create_order(self.waiter, table_number=1)
        response = self.admin_client.post(
            f"/api/pedidos/{order.id}/items",
            {"name": "Tinto", "price": "2000"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.admin_client.post(f"/api/pedidos/{order.id}/enviar").status_code, 403
        )


class CounterChargeTests(_Fixture):
    def test_charging_a_counter_order_touches_no_table(self):
        order = self._build_counter_order()
        response = self.admin_client.post(
            f"/api/pedidos/{order.id}/cobrar",
            {"account_id": self.account.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "CHARGED")
        self.assertFalse(Table.objects.exclude(status=Table.Status.FREE).exists())

        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.amount, Decimal("6000"))
        receipt = build_receipt_text(order, payment)
        self.assertIn("Mostrador", receipt)
        self.assertNotIn("Mesa", receipt)

    def test_voiding_the_charge_returns_it_to_in_progress(self):
        order = self._build_counter_order()
        charge_order(order, self.admin, self.account)
        void_charge(order, self.admin, "se cobró con la cuenta equivocada")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.IN_PROGRESS)

    def test_voiding_a_counter_order_frees_nothing_and_works(self):
        order = self._build_counter_order()
        services.void_order(order, self.admin, "cliente se fue")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.VOIDED)

    def test_the_admin_can_delete_their_empty_counter_draft(self):
        order_id = self._create(self.admin_client).data["id"]
        response = self.admin_client.delete(f"/api/pedidos/{order_id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Order.objects.filter(pk=order_id).exists())
