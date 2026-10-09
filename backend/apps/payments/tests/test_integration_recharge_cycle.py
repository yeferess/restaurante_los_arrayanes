from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.orders import services
from apps.payments.models import Payment, PaymentAccount

User = get_user_model()


class ChargeVoidRechargeCycleTests(APITestCase):
    """T24 — full cycle: charge -> void with a reason -> recharge with
    a different account (RF-6, RF-7)."""

    def test_charge_void_recharge_keeps_a_clean_history(self):
        services.resize_tables(1)
        waiter = User.objects.create_user(
            username="cycle_w", password="1234", role=User.Role.MESERO
        )
        admin = User.objects.create_user(
            username="cycle_admin", password="clave1234", role=User.Role.ADMIN
        )
        order = services.create_order(waiter, table_number=1)
        services.add_item(order, name="Limonada", price=Decimal("4.50"))
        services.send_order(order)

        efectivo = PaymentAccount.objects.get(name="Efectivo")
        nequi = PaymentAccount.objects.create(name="Nequi #1234")

        self.client.force_authenticate(admin)

        first_charge = self.client.post(
            f"/api/pedidos/{order.id}/cobrar",
            {"account_id": efectivo.id},
            format="json",
        )
        self.assertEqual(first_charge.status_code, 200)
        self.assertEqual(first_charge.data["status"], "CHARGED")

        void = self.client.post(
            f"/api/pedidos/{order.id}/cobro/anular",
            {"reason": "Cuenta equivocada"},
            format="json",
        )
        self.assertEqual(void.status_code, 200)
        self.assertEqual(void.data["status"], "IN_PROGRESS")
        self.assertIsNone(void.data["active_payment"])

        second_charge = self.client.post(
            f"/api/pedidos/{order.id}/cobrar",
            {"account_id": nequi.id},
            format="json",
        )
        self.assertEqual(second_charge.status_code, 200)
        self.assertEqual(
            second_charge.data["active_payment"]["account_name"], "Nequi #1234"
        )

        payments = Payment.objects.filter(order=order).order_by("id")
        self.assertEqual(payments.count(), 2)
        voided, active = payments
        self.assertEqual(voided.status, Payment.Status.VOIDED)
        self.assertEqual(voided.account, efectivo)
        self.assertEqual(voided.void_reason, "Cuenta equivocada")
        self.assertEqual(active.status, Payment.Status.ACTIVE)
        self.assertEqual(active.account, nequi)
