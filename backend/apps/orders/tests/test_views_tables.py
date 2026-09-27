from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()

TABLES_URL = "/api/mesas"


class TableListViewTests(APITestCase):
    """T25 — GET /api/mesas (RF-1, RF-13)."""

    def setUp(self):
        services.resize_tables(2)
        self.admin = User.objects.create_user(
            username="admin_tables", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_tables", password="1234", role=User.Role.MESERO
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_tables", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_tables", "pin": "1234"}
        )

    def test_without_session_returns_401(self):
        response = self.client.get(TABLES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_sees_all_tables(self):
        self._login_admin()
        response = self.client.get(TABLES_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_mesero_sees_all_tables(self):
        self._login_mesero()
        response = self.client.get(TABLES_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        numbers = [t["number"] for t in response.data]
        self.assertEqual(numbers, [1, 2])
