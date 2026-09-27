from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class RemoveItemViewTests(APITestCase):
    """T32 — DELETE /api/pedidos/{id}/items/{item_id} (RF-2)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_rm_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_rm", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )

    def _url(self, order_id, item_id):
        return f"/api/pedidos/{order_id}/items/{item_id}"

    def _login(self, username="mesero_rm_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_removing_in_draft(self):
        self._login()
        response = self.client.delete(self._url(self.order.id, self.item.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_removing_after_sending_returns_409(self):
        services.send_order(self.order)
        self._login()
        response = self.client.delete(self._url(self.order.id, self.item.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_waiter_cannot_remove(self):
        self._login("mesero_other_rm")
        response = self.client.delete(self._url(self.order.id, self.item.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_item_returns_404(self):
        self._login()
        response = self.client.delete(self._url(self.order.id, 999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.delete(self._url(self.order.id, self.item.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
