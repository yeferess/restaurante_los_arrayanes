from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class ResetMeseroPinViewTests(APITestCase):
    """T26 — POST /api/usuarios/meseros/{id}/reset-pin (RF-4)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_reset", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_reset", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_reset", "password": "Sup3rSecreta"},
        )

    def _url(self, mesero_id):
        return f"/api/usuarios/meseros/{mesero_id}/reset-pin"

    def test_reset_pin_changes_the_password(self):
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertFalse(self.mesero.check_password("1234"))
        self.assertTrue(self.mesero.check_password("9999"))

    def test_reset_pin_registers_exactly_one_traceability_row(self):
        self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        actions = AccountAction.objects.filter(
            account=self.mesero, action_type=AccountAction.ActionType.PIN_RESET
        )
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().performed_by, self.admin)

    def test_reset_pin_invalidates_the_mesero_active_session(self):
        mesero_client = self.client_class()
        login_response = mesero_client.post(
            "/api/auth/mesero/login", {"username": "mesero_reset", "pin": "1234"}
        )
        session_key = login_response.cookies["sessionid"].value
        self.assertTrue(SessionStore().exists(session_key))

        self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})

        self.assertFalse(SessionStore().exists(session_key))
        self.mesero.refresh_from_db()
        self.assertIsNone(self.mesero.current_session_key)

    def test_invalid_new_pin_returns_400(self):
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "12"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_mesero_returns_404(self):
        response = self.client.post(self._url(999999), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mesero_cannot_reset_pins(self):
        self.client.post("/api/auth/logout")
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_reset", "pin": "1234"}
        )
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_username_field_in_the_request_is_ignored(self):
        """RF-3: reset-pin can never change the mesero's username."""
        response = self.client.post(
            self._url(self.mesero.id),
            {"nuevo_pin": "9999", "username": "otro_nombre"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.username, "mesero_reset")

    def test_two_admins_resetting_the_same_pin_almost_at_once(self):
        """RF-4: last write wins, and both events are traced."""
        second_admin = User.objects.create_user(
            username="admin_reset_b", password="Sup3rSecreta", role=User.Role.ADMIN
        )

        first = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "1111"})
        second_client = self.client_class()
        second_client.post(
            "/api/auth/admin/login",
            {"username": "admin_reset_b", "password": "Sup3rSecreta"},
        )
        second = second_client.post(self._url(self.mesero.id), {"nuevo_pin": "2222"})

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)

        self.mesero.refresh_from_db()
        self.assertFalse(self.mesero.check_password("1111"))
        self.assertTrue(self.mesero.check_password("2222"))

        actions = AccountAction.objects.filter(
            account=self.mesero, action_type=AccountAction.ActionType.PIN_RESET
        ).order_by("id")
        self.assertEqual(actions.count(), 2)
        self.assertEqual(actions[0].performed_by, self.admin)
        self.assertEqual(actions[1].performed_by, second_admin)
