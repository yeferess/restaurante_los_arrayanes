from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

LOGOUT_URL = "/api/auth/logout"


class LogoutViewTests(APITestCase):
    """T22 — POST /api/auth/logout (RF-9)."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_logout", password="1234", role=User.Role.MESERO
        )

    def test_logout_without_session_returns_401(self):
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalidates_the_current_session(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_logout", "pin": "1234"}
        )

        first_response = self.client.post(LOGOUT_URL)
        self.assertEqual(first_response.status_code, status.HTTP_204_NO_CONTENT)

        second_response = self.client.post(LOGOUT_URL)
        self.assertEqual(second_response.status_code, status.HTTP_401_UNAUTHORIZED)
