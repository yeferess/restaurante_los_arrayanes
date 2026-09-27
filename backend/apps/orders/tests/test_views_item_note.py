from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

User = get_user_model()


class UpdateItemNoteViewTests(APITestCase):
    """T34 — PATCH /api/pedidos/{id}/items/{item_id}/nota (RF-4)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_note_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_note", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        self.item = services.add_item(
            self.order, name="Limonada", price=Decimal("4.50")
        )

    def _url(self, order_id, item_id):
        return f"/api/pedidos/{order_id}/items/{item_id}/nota"

    def _login(self, username="mesero_note_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_editing_the_note(self):
        self._login()
        response = self.client.patch(
            self._url(self.order.id, self.item.id),
            {"note": "sin azúcar"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["note"], "sin azúcar")

    def test_note_over_200_characters_returns_400(self):
        self._login()
        response = self.client.patch(
            self._url(self.order.id, self.item.id), {"note": "x" * 201}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_editing_a_voided_item_note_returns_409(self):
        services.send_order(self.order)
        services.void_item(self.order, self.item, self.waiter, "motivo")
        self._login()
        response = self.client.patch(
            self._url(self.order.id, self.item.id), {"note": "nueva"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_waiter_cannot_edit(self):
        self._login("mesero_other_note")
        response = self.client.patch(
            self._url(self.order.id, self.item.id), {"note": "nueva"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.patch(
            self._url(self.order.id, self.item.id), {"note": "nueva"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
