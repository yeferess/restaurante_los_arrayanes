from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class OrderPayloadDailyNumberTests(APITestCase):
    """T75 — numero_dia/enviado_en (daily_number/sent_at) travel with
    every order payload (RF-14)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_dn_payload", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_dn_payload", "pin": "1234"}
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))

    def test_draft_order_has_null_daily_number_and_sent_at(self):
        response = self.client.get(f"/api/pedidos/{self.order.id}")
        self.assertIsNone(response.data["daily_number"])
        self.assertIsNone(response.data["sent_at"])
        self.assertIn("id", response.data)

    def test_sending_fills_daily_number_and_sent_at_in_the_response(self):
        response = self.client.post(f"/api/pedidos/{self.order.id}/enviar")
        self.assertEqual(response.data["daily_number"], 1)
        self.assertIsNotNone(response.data["sent_at"])

    def test_my_orders_list_includes_daily_number(self):
        self.client.post(f"/api/pedidos/{self.order.id}/enviar")
        response = self.client.get("/api/pedidos/mios")
        self.assertEqual(response.data[0]["daily_number"], 1)


class TableActiveOrderDailyNumberTests(APITestCase):
    """T76 — active_order_daily_number on GET /api/mesas (RF-14,
    interacción con RF-13)."""

    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_dn_table", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_dn_other", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))

    def _login(self, username):
        self.client.post(
            "/api/auth/mesero/login", {"username": username, "pin": "1234"}
        )

    def test_free_table_has_null_active_order_daily_number(self):
        self._login("mesero_dn_table")
        response = self.client.get("/api/mesas")
        table_2 = next(t for t in response.data if t["number"] == 2)
        self.assertIsNone(table_2["active_order_daily_number"])

    def test_occupied_table_with_undraft_order_is_still_null(self):
        self._login("mesero_dn_table")
        response = self.client.get("/api/mesas")
        table_1 = next(t for t in response.data if t["number"] == 1)
        self.assertIsNone(table_1["active_order_daily_number"])

    def test_occupied_table_shows_the_daily_number_once_sent(self):
        services.send_order(self.order)
        self._login("mesero_dn_table")
        response = self.client.get("/api/mesas")
        table_1 = next(t for t in response.data if t["number"] == 1)
        self.assertEqual(table_1["active_order_daily_number"], 1)

    def test_visible_to_a_waiter_who_does_not_own_the_order(self):
        services.send_order(self.order)
        self._login("mesero_dn_other")
        response = self.client.get("/api/mesas")
        table_1 = next(t for t in response.data if t["number"] == 1)
        self.assertEqual(table_1["active_order_daily_number"], 1)

        # RF-13 still blocks the rest of the order's content.
        detail = self.client.get(f"/api/pedidos/{self.order.id}")
        self.assertEqual(detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_paid_table_shows_the_charged_orders_daily_number(self):
        services.send_order(self.order)
        admin = User.objects.create_user(
            username="admin_dn_table", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        from apps.payments.models import PaymentAccount
        from apps.payments.services import charge_order

        account = PaymentAccount.objects.get(name="Efectivo")
        charge_order(self.order, admin, account)

        self._login("mesero_dn_table")
        response = self.client.get("/api/mesas")
        table_1 = next(t for t in response.data if t["number"] == 1)
        self.assertEqual(table_1["active_order_daily_number"], 1)
