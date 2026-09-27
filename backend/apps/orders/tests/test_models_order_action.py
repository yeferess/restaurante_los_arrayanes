from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.orders.models import Order, OrderAction, OrderItem

User = get_user_model()


class OrderActionModelTests(TestCase):
    """T06 — `OrderAction` model (RF-12)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_action", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_action", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = Order.objects.create(table_number=1, waiter=self.waiter)

    def test_item_voided_action(self):
        item = OrderItem.objects.create(
            order=self.order, name="Limonada", unit_price=Decimal("4.50")
        )
        action = OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.ITEM_VOIDED,
            performed_by=self.waiter,
            reason="Pedido por error",
            item=item,
        )
        self.assertEqual(action.action_type, OrderAction.ActionType.ITEM_VOIDED)
        self.assertEqual(action.item, item)

    def test_table_corrected_action_records_from_and_to(self):
        action = OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.TABLE_CORRECTED,
            performed_by=self.waiter,
            from_table_number=1,
            to_table_number=2,
        )
        self.assertEqual(action.from_table_number, 1)
        self.assertEqual(action.to_table_number, 2)

    def test_charged_action_has_no_reason(self):
        action = OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.CHARGED,
            performed_by=self.admin,
        )
        self.assertIsNone(action.reason)

    def test_order_voided_auto_action_type_exists(self):
        action = OrderAction.objects.create(
            order=self.order,
            action_type=OrderAction.ActionType.ORDER_VOIDED_AUTO,
            performed_by=self.waiter,
            reason="Se anularon todos los ítems",
        )
        self.assertEqual(action.action_type, "ORDER_VOIDED_AUTO")
