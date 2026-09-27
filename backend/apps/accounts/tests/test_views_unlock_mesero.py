from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class UnlockMeseroViewTests(APITestCase):
    """T28 — POST /api/usuarios/meseros/{id}/desbloquear (RF-3, RF-7)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_unlock", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_unlock", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_unlock", "password": "Sup3rSecreta"},
        )

    def _url(self, mesero_id):
        return f"/api/usuarios/meseros/{mesero_id}/desbloquear"

    def _lock_mesero(self):
        self.mesero.is_locked = True
        self.mesero.failed_login_attempts = 5
        self.mesero.save(update_fields=["is_locked", "failed_login_attempts"])

    def test_unlock_requires_nuevo_pin(self):
        self._lock_mesero()
        response = self.client.post(self._url(self.mesero.id), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unlocking_a_non_locked_account_returns_409(self):
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_unlock_sets_the_new_pin_and_clears_the_lock(self):
        self._lock_mesero()
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.mesero.refresh_from_db()
        self.assertFalse(self.mesero.is_locked)
        self.assertIsNone(self.mesero.locked_at)
        self.assertEqual(self.mesero.failed_login_attempts, 0)
        self.assertTrue(self.mesero.check_password("9999"))
        self.assertFalse(self.mesero.check_password("1234"))

    def test_unlock_registers_exactly_one_traceability_row(self):
        self._lock_mesero()
        self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        actions = AccountAction.objects.filter(
            account=self.mesero, action_type=AccountAction.ActionType.UNLOCKED
        )
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().performed_by, self.admin)

    def test_new_pin_works_for_the_next_login(self):
        self._lock_mesero()
        self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})

        login_response = self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_unlock", "pin": "9999"}
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_invalid_new_pin_returns_400(self):
        self._lock_mesero()
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "12"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_mesero_returns_404(self):
        response = self.client.post(self._url(999999), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mesero_cannot_unlock_accounts(self):
        self._lock_mesero()
        self.client.post("/api/auth/logout")
        # Can't log in as the locked mesero itself; use a second one instead.
        other_mesero = User.objects.create_user(
            username="mesero_unlock2", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_unlock2", "pin": "1234"}
        )
        response = self.client.post(self._url(self.mesero.id), {"nuevo_pin": "9999"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_username_field_in_the_request_is_ignored(self):
        """RF-3: unlocking can never change the mesero's username."""
        self._lock_mesero()
        response = self.client.post(
            self._url(self.mesero.id),
            {"nuevo_pin": "9999", "username": "otro_nombre"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.username, "mesero_unlock")
