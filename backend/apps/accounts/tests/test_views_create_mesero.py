from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()

CREATE_MESERO_URL = "/api/usuarios/meseros"


class CreateMeseroViewTests(APITestCase):
    """T25 — POST /api/usuarios/meseros (RF-2)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_create", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_create", password="1234", role=User.Role.MESERO
        )

    def _login_as_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_create", "password": "Sup3rSecreta"},
        )

    def _login_as_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_create", "pin": "1234"}
        )

    def test_admin_creates_mesero_with_valid_data(self):
        self._login_as_admin()
        response = self.client.post(
            CREATE_MESERO_URL, {"username": "nuevo_mesero", "pin": "5678"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "nuevo_mesero")
        self.assertEqual(response.data["role"], "MESERO")
        self.assertTrue(response.data["is_active"])
        self.assertEqual(response.data["created_by"], self.admin.id)

        created = User.objects.get(username="nuevo_mesero")
        self.assertTrue(created.check_password("5678"))
        self.assertEqual(created.created_by, self.admin)
        self.assertTrue(
            AccountAction.objects.filter(
                account=created,
                action_type=AccountAction.ActionType.CREATED,
                performed_by=self.admin,
            ).exists()
        )

    def test_mesero_cannot_create_a_mesero(self):
        self._login_as_mesero()
        response = self.client.post(
            CREATE_MESERO_URL, {"username": "otro_mesero", "pin": "5678"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_username_returns_409(self):
        self._login_as_admin()
        response = self.client.post(
            CREATE_MESERO_URL, {"username": "mesero_create", "pin": "5678"}
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_invalid_pin_returns_400(self):
        self._login_as_admin()
        response = self.client.post(
            CREATE_MESERO_URL, {"username": "otro_mesero2", "pin": "12"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
