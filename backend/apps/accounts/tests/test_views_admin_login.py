from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

LOGIN_URL = "/api/auth/admin/login"


class AdminLoginViewTests(APITestCase):
    """T20 — POST /api/auth/admin/login (RF-1, RF-7, RF-8)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_view", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_valid_credentials_return_200_and_set_session_cookie(self):
        response = self.client.post(
            LOGIN_URL, {"username": "admin_view", "password": "Sup3rSecreta"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "admin_view")
        self.assertEqual(response.data["role"], "ADMIN")
        self.assertIn("sessionid", response.cookies)

    def test_invalid_credentials_return_401_with_remaining_attempts(self):
        response = self.client.post(
            LOGIN_URL, {"username": "admin_view", "password": "wrong"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("intentos_restantes", response.data)
        self.assertEqual(response.data["intentos_restantes"], 4)

    def test_locked_account_returns_423(self):
        self.admin.is_locked = True
        self.admin.save(update_fields=["is_locked"])
        response = self.client.post(
            LOGIN_URL, {"username": "admin_view", "password": "Sup3rSecreta"}
        )
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)

    def test_deactivated_account_returns_403(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        response = self.client.post(
            LOGIN_URL, {"username": "admin_view", "password": "Sup3rSecreta"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mesero_cannot_login_through_the_admin_endpoint(self):
        User.objects.create_user(
            username="mesero_view", password="1234", role=User.Role.MESERO
        )
        response = self.client.post(
            LOGIN_URL, {"username": "mesero_view", "password": "1234"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_five_real_failed_attempts_lock_an_admin_account(self):
        """RF-7: the real lockout path also locks an admin, not just a mesero."""
        for _ in range(4):
            response = self.client.post(
                LOGIN_URL, {"username": "admin_view", "password": "wrong"}
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        fifth = self.client.post(
            LOGIN_URL, {"username": "admin_view", "password": "wrong"}
        )
        self.assertEqual(fifth.status_code, status.HTTP_423_LOCKED)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_locked)
        self.assertIsNotNone(self.admin.locked_at)
