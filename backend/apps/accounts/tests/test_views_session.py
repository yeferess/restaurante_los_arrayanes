from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

SESSION_URL = "/api/auth/session"


class SessionInfoViewTests(APITestCase):
    """T24 — GET /api/auth/session (RF-1 support)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_session", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_returns_401_without_a_session(self):
        response = self.client.get(SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_user_info_with_a_valid_session(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_session", "password": "Sup3rSecreta"},
        )
        response = self.client.get(SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "admin_session")
        self.assertEqual(response.data["role"], "ADMIN")
        self.assertEqual(response.data["id"], self.admin.id)
