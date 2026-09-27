from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AccountAction

User = get_user_model()


class LockoutUnlockLoginFlowTests(APITestCase):
    """T41 — end-to-end: 5 failures -> 423 -> admin unlocks with a new PIN
    -> login succeeds with that PIN (RF-3, RF-4, RF-7, RF-11)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_flow", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_flow", password="1234", role=User.Role.MESERO
        )

    def test_full_lockout_unlock_login_flow(self):
        for _ in range(5):
            response = self.client.post(
                "/api/auth/mesero/login", {"username": "mesero_flow", "pin": "wrong"}
            )
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        self.mesero.refresh_from_db()
        self.assertTrue(self.mesero.is_locked)

        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_flow", "password": "Sup3rSecreta"},
        )
        unlock_response = self.client.post(
            f"/api/usuarios/meseros/{self.mesero.id}/desbloquear", {"nuevo_pin": "9999"}
        )
        self.assertEqual(unlock_response.status_code, status.HTTP_200_OK)
        self.client.post("/api/auth/logout")

        old_pin_response = self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_flow", "pin": "1234"}
        )
        self.assertEqual(old_pin_response.status_code, status.HTTP_401_UNAUTHORIZED)

        new_pin_response = self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_flow", "pin": "9999"}
        )
        self.assertEqual(new_pin_response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            AccountAction.objects.filter(
                account=self.mesero,
                action_type=AccountAction.ActionType.AUTO_LOCKED,
            ).exists()
        )
        self.assertTrue(
            AccountAction.objects.filter(
                account=self.mesero,
                action_type=AccountAction.ActionType.UNLOCKED,
                performed_by=self.admin,
                via_cli=False,
            ).exists()
        )
