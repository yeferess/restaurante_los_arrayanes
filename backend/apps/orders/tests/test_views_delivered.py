from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class SetDeliveredViewTests(APITestCase):
    """T37 — POST /api/pedidos/{id}/entregado (RF-8)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_deliv_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_deliv", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/entregado"

    def _login(self, username="mesero_deliv_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_marking_delivered(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"delivered": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["delivered"])

    def test_marking_a_voided_order_returns_409(self):
        self.order.status = Order.Status.VOIDED
        self.order.save(update_fields=["status"])
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"delivered": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_waiter_cannot_mark(self):
        self._login("mesero_other_deliv")
        response = self.client.post(
            self._url(self.order.id), {"delivered": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.order.id), {"delivered": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
