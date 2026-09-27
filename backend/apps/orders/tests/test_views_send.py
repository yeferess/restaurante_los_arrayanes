from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class SendOrderViewTests(APITestCase):
    """T35 — POST /api/pedidos/{id}/enviar (RF-5)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_send_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_send", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/enviar"

    def _login(self, username="mesero_send_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_sending_with_items(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        self._login()
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "IN_PROGRESS")

    def test_sending_empty_returns_409(self):
        self._login()
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_resending_is_a_no_op_200(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        self._login()
        self.client.post(self._url(self.order.id))
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_waiter_cannot_send(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        self._login("mesero_other_send")
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
