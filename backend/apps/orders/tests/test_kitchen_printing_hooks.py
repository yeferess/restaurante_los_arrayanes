from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.orders import services
from apps.orders.models import Order

User = get_user_model()


class SendOrderPrintHookTests(TestCase):
    """T19 — send_order() ("Crear pedido") never prints: printing is a
    separate, explicit action (004 RF-1, "Imprimir pedido")."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="hook_send", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))

    @patch("apps.kitchen_printing.services.register_event_and_print")
    def test_sending_a_draft_does_not_print(self, mock_register):
        services.send_order(self.order)
        mock_register.assert_not_called()

    @patch("apps.kitchen_printing.services.register_event_and_print")
    def test_resending_an_already_sent_order_does_not_trigger_printing(
        self, mock_register
    ):
        mock_register.return_value = None
        services.send_order(self.order)
        mock_register.reset_mock()
        services.send_order(self.order)
        mock_register.assert_not_called()


class AddItemPrintHookTests(TestCase):
    """T20 — add_item() never prints, not even an addition (RF-1)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="hook_add", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    @patch("apps.kitchen_printing.services.register_event_and_print")
    def test_adding_an_item_to_a_draft_does_not_trigger_printing(self, mock_register):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        mock_register.assert_not_called()

    @patch("apps.kitchen_printing.services.register_event_and_print")
    def test_adding_an_item_after_sending_does_not_print(self, mock_register):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        services.add_item(self.order, name="Jugo", price=Decimal("5.00"))
        mock_register.assert_not_called()


class VoidItemPrintHookTests(TestCase):
    """T21 — void_item() never prints: the void waits for the next
    "Imprimir pedido" (RF-1)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="hook_void", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, table_number=1)

    @patch("apps.kitchen_printing.services.register_event_and_print")
    def test_voiding_one_of_several_items_does_not_print(self, mock_register):
        item1 = services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.add_item(self.order, name="Jugo", price=Decimal("5.00"))
        services.send_order(self.order)
        services.void_item(self.order, item1, self.waiter, "cliente se arrepintio")
        mock_register.assert_not_called()

    @patch("apps.kitchen_printing.services.register_event_and_print")
    def test_voiding_the_last_item_auto_voids_the_order_without_printing(
        self, mock_register
    ):
        mock_register.return_value = None
        item1 = services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        mock_register.reset_mock()
        services.void_item(self.order, item1, self.waiter, "cliente se arrepintio")
        mock_register.assert_not_called()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.VOIDED)
