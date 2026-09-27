from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class VoidItemViewTests(APITestCase):
    """T33 — POST /api/pedidos/{id}/items/{item_id}/anular (RF-6)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_void_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_void", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )
        self.item2 = services.add_item(self.order, name="Te", price=Decimal("3.00"))
        services.send_order(self.order)

    def _url(self, order_id, item_id):
        return f"/api/pedidos/{order_id}/items/{item_id}/anular"

    def _login(self, username="mesero_void_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_voiding_with_reason(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id, self.item.id),
            {"reason": "Pedido por error"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_reason_returns_400(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id, self.item.id), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_voiding_a_draft_order_item_returns_409(self):
        self.order.status = Order.Status.DRAFT
        self.order.save(update_fields=["status"])
        self._login()
        response = self.client.post(
            self._url(self.order.id, self.item.id),
            {"reason": "motivo"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_waiter_cannot_void(self):
        self._login("mesero_other_void")
        response = self.client.post(
            self._url(self.order.id, self.item.id),
            {"reason": "motivo"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_item_returns_404(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id, 999999), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.order.id, self.item.id),
            {"reason": "motivo"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
