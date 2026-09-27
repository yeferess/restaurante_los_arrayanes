from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()

RESIZE_URL = "/api/mesas/numero"


class ResizeTablesViewTests(APITestCase):
    """T26 — PATCH /api/mesas/numero (RF-1)."""

    def setUp(self):
        services.resize_tables(2)
        self.admin = User.objects.create_user(
            username="admin_resize", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_resize", password="1234", role=User.Role.MESERO
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_resize", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_resize", "pin": "1234"}
        )

    def test_admin_can_grow_the_table_count(self):
        self._login_admin()
        response = self.client.patch(
            RESIZE_URL, {"numero": 4}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_mesero_cannot_resize(self):
        self._login_mesero()
        response = self.client.patch(RESIZE_URL, {"numero": 4}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_number_returns_400(self):
        self._login_admin()
        response = self.client.patch(RESIZE_URL, {"numero": 0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shrinking_with_a_non_free_table_returns_409(self):
        services.create_order(self.mesero, table_number=2)
        self._login_admin()
        response = self.client.patch(RESIZE_URL, {"numero": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_without_session_returns_401(self):
        response = self.client.patch(RESIZE_URL, {"numero": 3}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
