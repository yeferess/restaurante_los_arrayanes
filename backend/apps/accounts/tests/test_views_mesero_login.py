from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

LOGIN_URL = "/api/auth/mesero/login"


class MeseroLoginViewTests(APITestCase):
    """T21 — POST /api/auth/mesero/login (RF-1, RF-7, RF-9)."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_view", password="1234", role=User.Role.MESERO
        )

    def test_valid_credentials_return_200_and_set_session_cookie(self):
        response = self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "MESERO")
        self.assertIn("sessionid", response.cookies)

    def test_invalid_pin_returns_401_with_remaining_attempts(self):
        response = self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "0000"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["intentos_restantes"], 4)

    def test_locked_account_returns_423(self):
        self.mesero.is_locked = True
        self.mesero.save(update_fields=["is_locked"])
        response = self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)

    def test_deactivated_account_returns_403(self):
        self.mesero.is_active = False
        self.mesero.save(update_fields=["is_active"])
        response = self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_login_through_the_mesero_endpoint(self):
        User.objects.create_user(
            username="admin_view2", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        response = self.client.post(
            LOGIN_URL, {"username": "admin_view2", "pin": "Sup3rSecreta"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_second_login_invalidates_the_first_device_session(self):
        client_a = APIClient()
        client_b = APIClient()

        response_a = client_a.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})
        session_key_a = response_a.cookies["sessionid"].value
        self.assertTrue(SessionStore().exists(session_key_a))

        response_b = client_b.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

        self.assertFalse(SessionStore().exists(session_key_a))

    def test_a_request_with_the_stale_cookie_gets_rejected(self):
        """T42 — the exact HTTP-level check: device A's old cookie stops
        authenticating once device B logs in (RF-9)."""
        client_a = APIClient()
        client_b = APIClient()

        client_a.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})
        client_b.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})

        stale_response = client_a.get("/api/auth/session")
        self.assertEqual(stale_response.status_code, status.HTTP_401_UNAUTHORIZED)

        fresh_response = client_b.get("/api/auth/session")
        self.assertEqual(fresh_response.status_code, status.HTTP_200_OK)

    def test_session_survives_indefinite_inactivity(self):
        """RF-9: unlike RF-8's admin timeout, a mesero session never expires
        from inactivity — the admin inactivity middleware must ignore it
        even if a stale 'last activity' marker were present."""
        self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "1234"})

        session = self.client.session
        session["ultima_actividad"] = "2000-01-01T00:00:00+00:00"
        session.save()

        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "MESERO")

    @patch("apps.accounts.views.has_open_tables", return_value=True)
    def test_lockout_happens_even_with_open_tables(self, _mock):
        """RF-7: the automatic lockout admits no exceptions, unlike RF-5's
        deactivation. has_open_tables isn't even consulted by login."""
        for _ in range(4):
            self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "wrong"})

        fifth = self.client.post(LOGIN_URL, {"username": "mesero_view", "pin": "wrong"})
        self.assertEqual(fifth.status_code, status.HTTP_423_LOCKED)
        self.mesero.refresh_from_db()
        self.assertTrue(self.mesero.is_locked)
