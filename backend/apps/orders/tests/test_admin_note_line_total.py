from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class AdminNoteTests(APITestCase):
    """003 RF-17 — PATCH /api/pedidos/{id}/nota-admin; the note never
    reaches a waiter. Also RF-3's per-line total."""

    def setUp(self):
        services.resize_tables(1)
        User.objects.create_user(
            username="admin_note", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="mesero_note", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, 1)
        services.add_item(self.order, name="Sopa", price=8000, quantity=3)
        self.url = f"/api/pedidos/{self.order.id}/nota-admin"

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_note", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_note", "pin": "1234"}
        )

    def test_admin_saves_the_note(self):
        self._login_admin()
        response = self.client.patch(self.url, {"note": "  mesa de cumpleanos "})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["admin_note"], "mesa de cumpleanos")
        self.order.refresh_from_db()
        self.assertEqual(self.order.admin_note, "mesa de cumpleanos")
        detail = self.client.get(f"/api/pedidos/{self.order.id}")
        self.assertEqual(detail.data["admin_note"], "mesa de cumpleanos")

    def test_too_long_note_returns_400(self):
        self._login_admin()
        response = self.client.patch(self.url, {"note": "x" * 301})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_order_returns_404(self):
        self._login_admin()
        response = self.client.patch("/api/pedidos/999999/nota-admin", {"note": "x"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mesero_cannot_write_or_read_it(self):
        Order.objects.filter(pk=self.order.pk).update(admin_note="secreto")
        self._login_mesero()
        self.assertEqual(
            self.client.patch(self.url, {"note": "x"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        mine = self.client.get("/api/pedidos/mios")
        self.assertNotIn("admin_note", mine.data[0])
        detail = self.client.get(f"/api/pedidos/{self.order.id}")
        self.assertNotIn("admin_note", detail.data)

    def test_items_carry_their_line_total(self):
        self._login_mesero()
        detail = self.client.get(f"/api/pedidos/{self.order.id}")
        self.assertEqual(detail.data["items"][0]["line_total"], "24000.00")
