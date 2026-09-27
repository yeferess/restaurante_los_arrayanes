from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()

CREATE_ADMIN_URL = "/api/usuarios/admins"


class CreateAdminViewTests(APITestCase):
    """T29 — POST /api/usuarios/admins (RF-6, RF-10)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_creator", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_create_admin", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_creator", "password": "Sup3rSecreta"},
        )

    def test_admin_creates_another_admin_with_valid_data(self):
        response = self.client.post(
            CREATE_ADMIN_URL, {"username": "nuevo_admin", "password": "OtraSegura9"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "nuevo_admin")
        self.assertEqual(response.data["role"], "ADMIN")
        self.assertEqual(response.data["created_by"], self.admin.id)

        created = User.objects.get(username="nuevo_admin")
        self.assertTrue(created.check_password("OtraSegura9"))
        self.assertTrue(
            AccountAction.objects.filter(
                account=created,
                action_type=AccountAction.ActionType.ADMIN_CREATED,
                performed_by=self.admin,
            ).exists()
        )

    def test_duplicate_username_returns_409(self):
        response = self.client.post(
            CREATE_ADMIN_URL, {"username": "admin_creator", "password": "OtraSegura9"}
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_weak_password_returns_400(self):
        response = self.client.post(
            CREATE_ADMIN_URL, {"username": "nuevo_admin2", "password": "abc"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mesero_cannot_create_admins(self):
        self.client.post("/api/auth/logout")
        self.client.post(
            "/api/auth/mesero/login",
            {"username": "mesero_create_admin", "pin": "1234"},
        )
        response = self.client.post(
            CREATE_ADMIN_URL, {"username": "nuevo_admin3", "password": "OtraSegura9"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
