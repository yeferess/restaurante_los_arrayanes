from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()

INCOMING_URL = "/api/pedidos/entrantes"


class IncomingOrdersViewTests(APITestCase):
    """T29 — GET /api/pedidos/entrantes (soporta RF-9, RF-11)."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_incoming", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_incoming", password="Sup3rSecreta", role=User.Role.ADMIN
        )

        self.draft_order = services.create_order(self.waiter, table_number=1)

        self.sent_order = services.create_order(self.waiter, table_number=2)
        services.add_item(self.sent_order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.sent_order)

        self.charged_order = services.create_order(self.waiter, table_number=3)
        services.add_item(self.charged_order, name="Te", price=Decimal("3.00"))
        services.send_order(self.charged_order)
        self.charged_order.status = Order.Status.CHARGED
        self.charged_order.save(update_fields=["status"])

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_incoming", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_incoming", "pin": "1234"}
        )

    def test_admin_sees_only_in_progress_orders(self):
        self._login_admin()
        response = self.client.get(INCOMING_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.sent_order.id)

    def test_mesero_cannot_see_incoming_orders(self):
        self._login_mesero()
        response = self.client.get(INCOMING_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
