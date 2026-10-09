from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders.models import Order, OrderItem, Table
from apps.payments import services
from apps.payments.models import PaymentAccount

User = get_user_model()


class ChargeOrderValidationAndAmountTests(TestCase):
    """T08 — charge_order(): validations and amount calculation
    (RF-1, RF-4)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_chg", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_chg", password="clave1234", role=User.Role.ADMIN
        )
        self.table = Table.objects.create(number=1, status=Table.Status.OCCUPIED)
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _in_progress_order(self):
        order = Order.objects.create(
            table_number=1, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        OrderItem.objects.create(
            order=order, name="Limonada natural", unit_price="4.50", quantity=2
        )
        OrderItem.objects.create(
            order=order, name="Sancocho de gallina", unit_price="20.00", quantity=1
        )
        voided = OrderItem.objects.create(
            order=order, name="Jugo de mora", unit_price="5.00", quantity=1
        )
        voided.is_voided = True
        voided.save(update_fields=["is_voided"])
        return order

    def test_rejects_a_draft_order(self):
        order = Order.objects.create(table_number=1, waiter=self.waiter)
        with self.assertRaises(ValidationError):
            services.charge_order(order, self.admin, self.account)

    def test_rejects_an_already_charged_order(self):
        order = Order.objects.create(
            table_number=1, waiter=self.waiter, status=Order.Status.CHARGED
        )
        with self.assertRaises(ValidationError):
            services.charge_order(order, self.admin, self.account)

    def test_rejects_a_voided_order(self):
        order = Order.objects.create(
            table_number=1, waiter=self.waiter, status=Order.Status.VOIDED
        )
        with self.assertRaises(ValidationError):
            services.charge_order(order, self.admin, self.account)

    def test_rejects_when_the_table_is_not_occupied(self):
        self.table.status = Table.Status.FREE
        self.table.save(update_fields=["status"])
        order = self._in_progress_order()
        with self.assertRaises(ValidationError):
            services.charge_order(order, self.admin, self.account)

    def test_amount_excludes_voided_items(self):
        order = self._in_progress_order()
        payment = services.charge_order(order, self.admin, self.account)
        self.assertEqual(payment.amount, Decimal("29.00"))


class ChargeOrderEffectsTests(TestCase):
    """T09 — charge_order(): creates the Payment and applies its
    effects on the order/table (RF-3, RF-5)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_chg2", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_chg2", password="clave1234", role=User.Role.ADMIN
        )
        self.table = Table.objects.create(number=2, status=Table.Status.OCCUPIED)
        self.account = PaymentAccount.objects.get(name="Efectivo")
        self.order = Order.objects.create(
            table_number=2, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        OrderItem.objects.create(
            order=self.order, name="Limonada natural", unit_price="4.50", quantity=1
        )

    def test_creates_an_active_payment_with_the_right_data(self):
        payment = services.charge_order(self.order, self.admin, self.account)
        self.assertEqual(payment.status, payment.Status.ACTIVE)
        self.assertEqual(payment.account, self.account)
        self.assertEqual(payment.charged_by, self.admin)
        self.assertIsNotNone(payment.charged_at)
        self.assertEqual(payment.order, self.order)

    def test_order_and_table_change_state(self):
        services.charge_order(self.order, self.admin, self.account)
        self.order.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CHARGED)
        self.assertEqual(self.table.status, Table.Status.PAID)

    def test_registers_the_charged_action(self):
        from apps.orders.models import OrderAction

        services.charge_order(self.order, self.admin, self.account)
        self.assertTrue(
            OrderAction.objects.filter(
                order=self.order,
                action_type=OrderAction.ActionType.CHARGED,
                performed_by=self.admin,
            ).exists()
        )


class ChargeOrderConcurrencyTests(TestCase):
    """T10 — charge_order(): the DB's `unique_active_payment_per_order`
    constraint rejects a concurrent double-charge of the same order
    (RF-1, RF-7)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_chg3", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_chg3", password="clave1234", role=User.Role.ADMIN
        )
        self.table = Table.objects.create(number=3, status=Table.Status.OCCUPIED)
        self.account = PaymentAccount.objects.get(name="Efectivo")
        self.order = Order.objects.create(
            table_number=3, waiter=self.waiter, status=Order.Status.IN_PROGRESS
        )
        OrderItem.objects.create(
            order=self.order, name="Limonada natural", unit_price="4.50", quantity=1
        )

    def test_rejects_a_second_charge_racing_against_the_first(self):
        services.charge_order(self.order, self.admin, self.account)
        # Simulate the race: another request's status checks had already
        # read "in_progress"/"occupied" before the first charge committed.
        self.order.status = Order.Status.IN_PROGRESS
        self.order.save(update_fields=["status"])
        self.table.status = Table.Status.OCCUPIED
        self.table.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            services.charge_order(self.order, self.admin, self.account)

        from apps.payments.models import Payment

        self.assertEqual(
            Payment.objects.filter(order=self.order, status=Payment.Status.ACTIVE).count(),
            1,
        )
