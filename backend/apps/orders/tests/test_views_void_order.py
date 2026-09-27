from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class VoidOrderViewTests(APITestCase):
    """T39 — POST /api/pedidos/{id}/anular (RF-11)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_vo_view", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_vo_view", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/anular"

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_vo_view", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_vo_view", "pin": "1234"}
        )

    def test_admin_voids_with_reason(self):
        self._login_admin()
        response = self.client.post(
            self._url(self.order.id), {"reason": "Cliente se fue"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "VOIDED")

    def test_missing_reason_returns_400(self):
        self._login_admin()
        response = self.client.post(self._url(self.order.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mesero_cannot_void_the_whole_order(self):
        self._login_mesero()
        response = self.client.post(
            self._url(self.order.id), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_voiding_a_charged_order_returns_409(self):
        self._login_admin()
        self.client.post(f"/api/pedidos/{self.order.id}/cobrar")
        response = self.client.post(
            self._url(self.order.id), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.order.id), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
