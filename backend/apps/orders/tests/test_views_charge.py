from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class ChargeOrderViewTests(APITestCase):
    """T38 — POST /api/pedidos/{id}/cobrar (RF-9)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_charge_view", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_charge_view", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/cobrar"

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_charge_view", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login",
            {"username": "mesero_charge_view", "pin": "1234"},
        )

    def test_admin_charges_the_order(self):
        self._login_admin()
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CHARGED")

    def test_mesero_cannot_charge(self):
        self._login_mesero()
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_charging_twice_returns_409(self):
        self._login_admin()
        self.client.post(self._url(self.order.id))
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_nonexistent_order_returns_404(self):
        self._login_admin()
        response = self.client.post(self._url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.post(self._url(self.order.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
