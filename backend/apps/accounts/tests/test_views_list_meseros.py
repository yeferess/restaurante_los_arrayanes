from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

MESEROS_URL = "/api/usuarios/meseros"


class ListMeserosViewTests(APITestCase):
    """GET /api/usuarios/meseros — lists every mesero so the admin panel
    can offer a dropdown instead of asking for a raw id."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_list_mes", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero1 = User.objects.create_user(
            username="mesero_list_a", password="1234", role=User.Role.MESERO
        )
        self.mesero2 = User.objects.create_user(
            username="mesero_list_b", password="1234", role=User.Role.MESERO
        )
        self.mesero2.is_active = False
        self.mesero2.save(update_fields=["is_active"])

    def _login_as_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_list_mes", "password": "Sup3rSecreta"},
        )

    def _login_as_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_list_a", "pin": "1234"}
        )

    def test_admin_lists_every_mesero_active_and_inactive(self):
        self._login_as_admin()
        response = self.client.get(MESEROS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = {item["username"] for item in response.data}
        self.assertEqual(usernames, {"mesero_list_a", "mesero_list_b"})
        by_username = {item["username"]: item for item in response.data}
        self.assertEqual(by_username["mesero_list_a"]["id"], self.mesero1.id)
        self.assertTrue(by_username["mesero_list_a"]["is_active"])
        self.assertFalse(by_username["mesero_list_b"]["is_active"])

    def test_mesero_cannot_list_meseros(self):
        self._login_as_mesero()
        response = self.client.get(MESEROS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.get(MESEROS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
