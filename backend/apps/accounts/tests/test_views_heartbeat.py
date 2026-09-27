from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

HEARTBEAT_URL = "/api/auth/heartbeat"


class HeartbeatAndInactivityTests(APITestCase):
    """T23 — POST /api/auth/heartbeat + admin inactivity middleware (RF-8)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hb", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.client.post(
            "/api/auth/admin/login", {"username": "admin_hb", "password": "Sup3rSecreta"}
        )

    def _backdate_last_activity(self, minutes_ago):
        session = self.client.session
        session["ultima_actividad"] = (
            timezone.now() - timedelta(minutes=minutes_ago)
        ).isoformat()
        session.save()

    def test_heartbeat_refreshes_activity_and_returns_expiry(self):
        response = self.client.post(HEARTBEAT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["expira_en_seg"], 1800)

    def test_no_heartbeat_for_31_minutes_locks_out_the_next_admin_request(self):
        self._backdate_last_activity(minutes_ago=31)
        response = self.client.post(HEARTBEAT_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_activity_within_30_minutes_keeps_the_session_alive(self):
        self._backdate_last_activity(minutes_ago=29)
        response = self.client.post(HEARTBEAT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_repeated_heartbeats_keep_the_session_alive_indefinitely(self):
        # Simulate three consecutive pings, each within 30 min of the last.
        for _ in range(3):
            self._backdate_last_activity(minutes_ago=25)
            response = self.client.post(HEARTBEAT_URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_heartbeat_requires_an_admin_session(self):
        self.client.post("/api/auth/logout")
        response = self.client.post(HEARTBEAT_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
