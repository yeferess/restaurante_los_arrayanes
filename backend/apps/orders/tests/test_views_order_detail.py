from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class OrderDetailViewTests(APITestCase):
    """T30 — GET /api/pedidos/{id} (RF-13)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_detail", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_detail", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_detail", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}"

    def test_owner_sees_the_detail(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_detail", "pin": "1234"}
        )
        response = self.client.get(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order.id)

    def test_admin_sees_any_order_detail(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_detail", "password": "Sup3rSecreta"},
        )
        response = self.client.get(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_waiter_cannot_see_the_detail(self):
        self.client.post(
            "/api/auth/mesero/login",
            {"username": "mesero_other_detail", "pin": "1234"},
        )
        response = self.client.get(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_order_returns_404(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_detail", "pin": "1234"}
        )
        response = self.client.get(self._url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.get(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
