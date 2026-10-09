from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders.models import Order, OrderItem, Table
from apps.payments import services
from apps.payments.models import PaymentAccount

User = get_user_model()


class VoidChargeValidationTests(TestCase):
    """T11 — void_charge(): validations (RF-6)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_vc", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_vc", password="clave1234", role=User.Role.ADMIN
        )
        self.table = Table.objects.create(number=1, status=Table.Status.OCCUPIED)
        self.account = PaymentAccount.objects.get(name="Efectivo")
        self.order = Order.objects.create(
            table_number=1, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        OrderItem.objects.create(
            order=self.order, name="Limonada natural", unit_price="4.50", quantity=1
        )

    def test_rejects_when_there_is_no_active_charge(self):
        with self.assertRaises(ValidationError):
            services.void_charge(self.order, self.admin, "Error de caja")

    def test_rejects_an_empty_reason(self):
        services.charge_order(self.order, self.admin, self.account)
        with self.assertRaises(ValidationError):
            services.void_charge(self.order, self.admin, "")

    def test_rejects_voiding_an_already_voided_charge(self):
        services.charge_order(self.order, self.admin, self.account)
        services.void_charge(self.order, self.admin, "Primer error")
        with self.assertRaises(ValidationError):
            services.void_charge(self.order, self.admin, "Segundo intento")


class VoidChargeTableReassignedTests(TestCase):
    """T12 — void_charge(): blocked if the table was reassigned to a
    new active order (RF-6, protects 003 RF-2)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_vc2", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_vc2", password="clave1234", role=User.Role.ADMIN
        )
        self.table = Table.objects.create(number=2, status=Table.Status.OCCUPIED)
        self.account = PaymentAccount.objects.get(name="Efectivo")
        self.order = Order.objects.create(
            table_number=2, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        OrderItem.objects.create(
            order=self.order, name="Limonada natural", unit_price="4.50", quantity=1
        )
        services.charge_order(self.order, self.admin, self.account)

    def test_blocked_when_the_table_has_a_new_active_order(self):
        self.table.status = Table.Status.FREE
        self.table.save(update_fields=["status"])
        new_order = Order.objects.create(
            table_number=2, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )

        with self.assertRaises(ValidationError):
            services.void_charge(self.order, self.admin, "Cuenta equivocada")

        from apps.payments.models import Payment

        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, Payment.Status.ACTIVE)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CHARGED)
        new_order.refresh_from_db()
        self.assertEqual(new_order.status, Order.Status.IN_PROGRESS)


class VoidChargeEffectsTests(TestCase):
    """T13 — void_charge(): effects of a successful void (RF-6)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_vc3", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_vc3", password="clave1234", role=User.Role.ADMIN
        )
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _charged_order(self, table_number):
        table = Table.objects.create(number=table_number, status=Table.Status.OCCUPIED)
        order = Order.objects.create(
            table_number=table_number, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        OrderItem.objects.create(
            order=order, name="Limonada natural", unit_price="4.50", quantity=1
        )
        services.charge_order(order, self.admin, self.account)
        return order, table

    def test_voids_the_payment_without_touching_its_other_fields(self):
        order, _ = self._charged_order(3)
        from apps.payments.models import Payment

        payment = Payment.objects.get(order=order)
        original_amount = payment.amount
        original_charged_by = payment.charged_by

        services.void_charge(order, self.admin, "Cuenta equivocada")

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.VOIDED)
        self.assertEqual(payment.voided_by, self.admin)
        self.assertEqual(payment.void_reason, "Cuenta equivocada")
        self.assertIsNotNone(payment.voided_at)
        self.assertEqual(payment.amount, original_amount)
        self.assertEqual(payment.charged_by, original_charged_by)

    def test_order_returns_to_in_progress(self):
        order, _ = self._charged_order(4)
        services.void_charge(order, self.admin, "Cuenta equivocada")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.IN_PROGRESS)

    def test_table_returns_to_occupied_if_still_paid(self):
        order, table = self._charged_order(5)
        services.void_charge(order, self.admin, "Cuenta equivocada")
        table.refresh_from_db()
        self.assertEqual(table.status, Table.Status.OCCUPIED)

    def test_table_is_left_untouched_if_already_freed(self):
        order, table = self._charged_order(6)
        table.status = Table.Status.FREE
        table.save(update_fields=["status"])

        services.void_charge(order, self.admin, "Cuenta equivocada")

        table.refresh_from_db()
        self.assertEqual(table.status, Table.Status.FREE)
