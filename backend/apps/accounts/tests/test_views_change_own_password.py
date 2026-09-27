from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()

CHANGE_PASSWORD_URL = "/api/usuarios/admins/me/password"


class ChangeOwnPasswordViewTests(APITestCase):
    """T30 — POST /api/usuarios/admins/me/password (RF-6)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_pw", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_pw", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_pw", "password": "Sup3rSecreta"},
        )

    def test_valid_change_returns_200_and_updates_password(self):
        response = self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "password_actual": "Sup3rSecreta",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "NuevaClave9",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("NuevaClave9"))

    def test_valid_change_registers_exactly_one_traceability_row(self):
        self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "password_actual": "Sup3rSecreta",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "NuevaClave9",
            },
        )
        actions = AccountAction.objects.filter(
            account=self.admin,
            action_type=AccountAction.ActionType.OWN_PASSWORD_CHANGED,
        )
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().performed_by, self.admin)

    def test_wrong_current_password_returns_400(self):
        response = self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "password_actual": "Incorrecta1",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "NuevaClave9",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Sup3rSecreta"))

    def test_mismatched_confirmation_returns_400(self):
        response = self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "password_actual": "Sup3rSecreta",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "OtraDistinta9",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_new_password_returns_400(self):
        response = self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "password_actual": "Sup3rSecreta",
                "password_nueva": "abc",
                "password_nueva_confirmacion": "abc",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mesero_cannot_use_this_endpoint(self):
        self.client.post("/api/auth/logout")
        self.client.post("/api/auth/mesero/login", {"username": "mesero_pw", "pin": "1234"})
        response = self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "password_actual": "1234",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "NuevaClave9",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
