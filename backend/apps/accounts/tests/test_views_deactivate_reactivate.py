from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class DeactivateReactivateMeseroViewTests(APITestCase):
    """T27 — POST .../desactivar and POST .../reactivar (RF-5)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_deact", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_deact", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_deact", "password": "Sup3rSecreta"},
        )

    def _deactivate_url(self, mesero_id):
        return f"/api/usuarios/meseros/{mesero_id}/desactivar"

    def _reactivate_url(self, mesero_id):
        return f"/api/usuarios/meseros/{mesero_id}/reactivar"

    @patch("apps.accounts.views.has_open_tables", return_value=False)
    def test_deactivate_without_open_tables_returns_200_and_blocks_login(self, _mock):
        response = self.client.post(self._deactivate_url(self.mesero.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertFalse(self.mesero.is_active)

        login_response = self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_deact", "pin": "1234"}
        )
        self.assertEqual(login_response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.accounts.views.has_open_tables", return_value=False)
    def test_deactivate_registers_exactly_one_traceability_row(self, _mock):
        self.client.post(self._deactivate_url(self.mesero.id))
        actions = AccountAction.objects.filter(
            account=self.mesero, action_type=AccountAction.ActionType.DEACTIVATED
        )
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().performed_by, self.admin)

    @patch("apps.accounts.views.has_open_tables", return_value=True)
    def test_deactivate_with_open_tables_returns_409(self, _mock):
        response = self.client.post(self._deactivate_url(self.mesero.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data["detail"], "El mesero tiene mesas o pedidos abiertos."
        )
        self.mesero.refresh_from_db()
        self.assertTrue(self.mesero.is_active)

    @patch("apps.accounts.views.has_open_tables", return_value=False)
    def test_reactivate_reverts_the_state(self, _mock):
        self.client.post(self._deactivate_url(self.mesero.id))
        response = self.client.post(self._reactivate_url(self.mesero.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertTrue(self.mesero.is_active)

    @patch("apps.accounts.views.has_open_tables", return_value=False)
    def test_reactivate_registers_exactly_one_traceability_row(self, _mock):
        self.client.post(self._deactivate_url(self.mesero.id))
        self.client.post(self._reactivate_url(self.mesero.id))
        actions = AccountAction.objects.filter(
            account=self.mesero, action_type=AccountAction.ActionType.ACTIVATED
        )
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().performed_by, self.admin)

    def test_reactivating_an_already_active_mesero_returns_409(self):
        response = self.client.post(self._reactivate_url(self.mesero.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_deactivate_nonexistent_mesero_returns_404(self):
        response = self.client.post(self._deactivate_url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reactivate_nonexistent_mesero_returns_404(self):
        response = self.client.post(self._reactivate_url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mesero_cannot_deactivate_or_reactivate(self):
        self.client.post("/api/auth/logout")
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_deact", "pin": "1234"}
        )
        response = self.client.post(self._deactivate_url(self.mesero.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.accounts.views.has_open_tables", return_value=False)
    def test_deactivate_ignores_an_injected_username_field(self, _mock):
        """RF-3: deactivating can never change the mesero's username."""
        response = self.client.post(
            self._deactivate_url(self.mesero.id), {"username": "otro_nombre"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.username, "mesero_deact")

    @patch("apps.accounts.views.has_open_tables", return_value=False)
    def test_deactivating_a_locked_mesero_does_not_require_unlocking_first(self, _mock):
        """RF-3: 'bloqueada' and 'desactivada' are independent states."""
        self.mesero.is_locked = True
        self.mesero.failed_login_attempts = 5
        self.mesero.save(update_fields=["is_locked", "failed_login_attempts"])

        response = self.client.post(self._deactivate_url(self.mesero.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertFalse(self.mesero.is_active)
        self.assertTrue(self.mesero.is_locked)
