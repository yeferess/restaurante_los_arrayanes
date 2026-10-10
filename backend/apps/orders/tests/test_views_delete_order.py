from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class DeleteOrderViewTests(APITestCase):
    """DELETE /api/pedidos/{id} — the mesero discards their own draft."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_del_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_del", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}"

    def _login(self, username):
        self.client.post(
            "/api/auth/mesero/login", {"username": username, "pin": "1234"}
        )

    def test_owner_deletes_a_draft(self):
        self._login("mesero_del_view")
        response = self.client.delete(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())

    def test_other_waiter_cannot_delete_it(self):
        self._login("mesero_other_del")
        response = self.client.delete(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_a_sent_order_returns_409(self):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        self._login("mesero_del_view")
        response = self.client.delete(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_nonexistent_order_returns_404(self):
        self._login("mesero_del_view")
        response = self.client.delete(self._url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.delete(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
