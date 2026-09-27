from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class FixTableViewTests(APITestCase):
    """T36 — POST /api/pedidos/{id}/mesa (RF-7)."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_fix_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_fix", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/mesa"

    def _login(self, username="mesero_fix_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_correcting_to_a_free_table(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"table_number": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["table_number"], 2)

    def test_correcting_to_the_same_table_returns_409(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"table_number": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_correcting_to_a_nonexistent_table_returns_400(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"table_number": 999}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_waiter_cannot_correct(self):
        self._login("mesero_other_fix")
        response = self.client.post(
            self._url(self.order.id), {"table_number": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.order.id), {"table_number": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
