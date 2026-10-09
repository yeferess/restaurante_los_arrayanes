from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.orders import services
from apps.payments.models import Payment, PaymentAccount

User = get_user_model()


class AccountListCreateViewTests(APITestCase):
    """T17 — GET/POST /api/cuentas-pago (RF-2, RF-8)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="acc_view_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="acc_view_w", password="1234", role=User.Role.MESERO
        )

    def _url(self):
        return "/api/cuentas-pago"

    def test_admin_lists_accounts_including_efectivo(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        names = [account["name"] for account in response.data]
        self.assertIn("Efectivo", names)

    def test_mesero_cannot_list_accounts(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)

    def test_without_session_returns_401(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 401)

    def test_admin_creates_an_account(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self._url(), {"name": "Nequi #1234"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Nequi #1234")
        self.assertFalse(response.data["is_fixed"])

    def test_empty_name_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self._url(), {"name": ""}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_duplicate_name_returns_409(self):
        self.client.force_authenticate(self.admin)
        self.client.post(self._url(), {"name": "Nequi #1234"}, format="json")
        response = self.client.post(
            self._url(), {"name": "Nequi #1234"}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_mesero_cannot_create_an_account(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.post(
            self._url(), {"name": "Nequi #1234"}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class AccountDeleteViewTests(APITestCase):
    """T18 — DELETE /api/cuentas-pago/{id} (RF-2, RF-8)."""

    def setUp(self):
        services.resize_tables(1)
        self.admin = User.objects.create_user(
            username="acc_del_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="acc_del_w", password="1234", role=User.Role.MESERO
        )
        self.account = PaymentAccount.objects.create(name="Nequi #1234")

    def _url(self, pk):
        return f"/api/cuentas-pago/{pk}"

    def test_admin_deletes_an_unused_account(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self._url(self.account.id))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(PaymentAccount.objects.filter(pk=self.account.pk).exists())

    def test_deleting_efectivo_returns_409(self):
        efectivo = PaymentAccount.objects.get(name="Efectivo")
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self._url(efectivo.id))
        self.assertEqual(response.status_code, 409)

    def test_deleting_an_account_in_use_returns_409(self):
        order = services.create_order(self.waiter, table_number=1)
        services.add_item(order, name="Limonada", price=Decimal("4.50"))
        services.send_order(order)
        from apps.payments import services as payment_services

        payment_services.charge_order(order, self.admin, self.account)

        self.client.force_authenticate(self.admin)
        response = self.client.delete(self._url(self.account.id))
        self.assertEqual(response.status_code, 409)

    def test_nonexistent_account_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self._url(999999))
        self.assertEqual(response.status_code, 404)

    def test_mesero_cannot_delete_an_account(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.delete(self._url(self.account.id))
        self.assertEqual(response.status_code, 403)

    def test_without_session_returns_401(self):
        response = self.client.delete(self._url(self.account.id))
        self.assertEqual(response.status_code, 401)
