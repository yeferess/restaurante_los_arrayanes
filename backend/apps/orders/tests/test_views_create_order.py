from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()

ORDERS_URL = "/api/pedidos"


class CreateOrderViewTests(APITestCase):
    """T27 — POST /api/pedidos (RF-2)."""

    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_create_view", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_create_view", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_create_view", "pin": "1234"}
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_create_view", "password": "Sup3rSecreta"},
        )

    def test_mesero_creates_an_order_on_a_free_table(self):
        self._login_mesero()
        response = self.client.post(
            ORDERS_URL, {"table_number": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "DRAFT")

    def test_creating_on_a_non_free_table_returns_409(self):
        self._login_mesero()
        self.client.post(ORDERS_URL, {"table_number": 1}, format="json")
        response = self.client.post(ORDERS_URL, {"table_number": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_admin_can_create_an_order_as_its_owner(self):
        """RF-18 (reforma de la regla 5): el admin también crea pedidos."""
        self._login_admin()
        response = self.client.post(ORDERS_URL, {"table_number": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["table_number"], 1)

    def test_without_session_returns_401(self):
        response = self.client.post(ORDERS_URL, {"table_number": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_table_returns_400(self):
        self._login_mesero()
        response = self.client.post(ORDERS_URL, {"table_number": 999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
