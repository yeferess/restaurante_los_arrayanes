from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import OrderAction
from apps.payments.models import PaymentAccount

User = get_user_model()


class OrderLifecycleFlowTests(APITestCase):
    """T59 — end-to-end: ajustar mesas → crear pedido → enviar → adición
    → anular ítem → corregir mesa → entregado → cobrar → liberar mesa
    (RF-1, RF-2, RF-3, RF-5, RF-6, RF-7, RF-8, RF-9, RF-10)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_flujo", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="mesero_flujo", password="1234", role=User.Role.MESERO
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_flujo", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_flujo", "pin": "1234"}
        )

    def test_full_lifecycle(self):
        # RF-1: ajustar el número de mesas
        self._login_admin()
        resize = self.client.patch(
            "/api/mesas/numero", {"numero": 2}, format="json"
        )
        self.assertEqual(resize.status_code, status.HTTP_200_OK)

        # RF-2: crear un pedido en una mesa libre
        self._login_mesero()
        create = self.client.post(
            "/api/pedidos", {"table_number": 1}, format="json"
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        order_id = create.data["id"]

        # RF-3: agregar un ítem fuera de carta
        add_item = self.client.post(
            f"/api/pedidos/{order_id}/items",
            {"name": "Limonada especial", "price": "4.50"},
            format="json",
        )
        self.assertEqual(add_item.status_code, status.HTTP_201_CREATED)
        first_item_id = add_item.data["id"]

        # RF-5: enviar el pedido
        send = self.client.post(f"/api/pedidos/{order_id}/enviar")
        self.assertEqual(send.status_code, status.HTTP_200_OK)
        self.assertEqual(send.data["status"], "IN_PROGRESS")

        # RF-5: agregar una adición
        addition = self.client.post(
            f"/api/pedidos/{order_id}/items",
            {"name": "Postre especial", "price": "6.00"},
            format="json",
        )
        self.assertEqual(addition.status_code, status.HTTP_201_CREATED)
        self.assertEqual(addition.data["line_type"], "ADDITION")

        # RF-6: anular el primer ítem, con motivo
        void_item = self.client.post(
            f"/api/pedidos/{order_id}/items/{first_item_id}/anular",
            {"reason": "El cliente cambió de opinión"},
            format="json",
        )
        self.assertEqual(void_item.status_code, status.HTTP_200_OK)
        self.assertTrue(
            OrderAction.objects.filter(
                order_id=order_id,
                action_type=OrderAction.ActionType.ITEM_VOIDED,
                performed_by=self.waiter,
                reason="El cliente cambió de opinión",
            ).exists()
        )

        # RF-7: corregir la mesa hacia la mesa 2 (libre)
        fix_table = self.client.post(
            f"/api/pedidos/{order_id}/mesa", {"table_number": 2}, format="json"
        )
        self.assertEqual(fix_table.status_code, status.HTTP_200_OK)
        self.assertEqual(fix_table.data["table_number"], 2)
        self.assertTrue(
            OrderAction.objects.filter(
                order_id=order_id,
                action_type=OrderAction.ActionType.TABLE_CORRECTED,
                from_table_number=1,
                to_table_number=2,
            ).exists()
        )

        # RF-8: marcar como entregado
        delivered = self.client.post(
            f"/api/pedidos/{order_id}/entregado", {"delivered": True}, format="json"
        )
        self.assertEqual(delivered.status_code, status.HTTP_200_OK)
        self.assertTrue(delivered.data["delivered"])

        # RF-9: el admin cobra el pedido
        self._login_admin()
        account = PaymentAccount.objects.get(name="Efectivo")
        charge = self.client.post(
            f"/api/pedidos/{order_id}/cobrar",
            {"account_id": account.id},
            format="json",
        )
        self.assertEqual(charge.status_code, status.HTTP_200_OK)
        self.assertEqual(charge.data["status"], "CHARGED")

        # RF-10: cualquier mesero libera la mesa ya pagada
        self._login_mesero()
        release = self.client.post("/api/mesas/2/liberar")
        self.assertEqual(release.status_code, status.HTTP_200_OK)
        self.assertEqual(release.data["status"], "FREE")
