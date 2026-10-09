from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Table

User = get_user_model()


class ReleaseTableViewTests(APITestCase):
    """T40 — POST /api/mesas/{numero}/liberar (RF-10)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_rel_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_rel", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_rel_view", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        table = Table.objects.get(number=1)
        table.status = Table.Status.PAID
        table.save(update_fields=["status"])

    def _url(self, table_number):
        return f"/api/mesas/{table_number}/liberar"

    def _login(self, username):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_any_waiter_can_release_a_paid_table(self):
        self._login("mesero_other_rel")
        response = self.client.post(self._url(1))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_cannot_release(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_rel_view", "password": "Sup3rSecreta"},
        )
        response = self.client.post(self._url(1))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_releasing_a_table_that_is_not_paid_returns_409(self):
        services.resize_tables(2)
        self._login("mesero_rel_view")
        response = self.client.post(self._url(2))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_nonexistent_table_returns_404(self):
        self._login("mesero_rel_view")
        response = self.client.post(self._url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.post(self._url(1))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
