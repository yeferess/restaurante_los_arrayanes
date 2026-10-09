from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.orders import services
from apps.payments.models import PaymentAccount

User = get_user_model()


class VoidChargeViewTests(APITestCase):
    """T16 — POST /api/pedidos/{id}/cobro/anular (RF-6, RF-8)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="vc_view_w", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="vc_view_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/cobro/anular"

    def _login_admin(self):
        self.client.force_authenticate(self.admin)

    def _charge(self):
        self.client.post(
            f"/api/pedidos/{self.order.id}/cobrar",
            {"account_id": self.account.id},
            format="json",
        )

    def test_admin_voids_the_charge(self):
        self._login_admin()
        self._charge()
        response = self.client.post(
            self._url(self.order.id), {"reason": "Cuenta equivocada"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["active_payment"])
        self.assertEqual(response.data["status"], "IN_PROGRESS")

    def test_missing_reason_returns_400(self):
        self._login_admin()
        self._charge()
        response = self.client.post(self._url(self.order.id), {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_mesero_cannot_void_a_charge(self):
        self._charge_as_admin_then_login_mesero()
        response = self.client.post(
            self._url(self.order.id), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def _charge_as_admin_then_login_mesero(self):
        self.client.force_authenticate(self.admin)
        self._charge()
        self.client.force_authenticate(self.waiter)

    def test_no_active_charge_returns_404(self):
        self._login_admin()
        response = self.client.post(
            self._url(self.order.id), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_table_reassigned_returns_409(self):
        self._login_admin()
        self._charge()
        from apps.orders.models import Table

        table = Table.objects.get(number=1)
        table.status = Table.Status.FREE
        table.save(update_fields=["status"])
        services.create_order(self.waiter, table_number=1)

        response = self.client.post(
            self._url(self.order.id), {"reason": "Cuenta equivocada"}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_already_voided_charge_returns_409(self):
        self._login_admin()
        self._charge()
        self.client.post(self._url(self.order.id), {"reason": "primero"}, format="json")
        response = self.client.post(
            self._url(self.order.id), {"reason": "segundo"}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.order.id), {"reason": "motivo"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
