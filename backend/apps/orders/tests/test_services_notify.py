from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.orders import services

User = get_user_model()


class NotifyOrdersChangedTests(TestCase):
    """T23 — notify_orders_changed() is called from, and only from, the
    right places (plan.md, section 4)."""

    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_notify", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_notify", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)

    @patch("apps.orders.services.notify_orders_changed")
    def test_creating_a_draft_order_does_not_notify(self, mock_notify):
        services.create_order(self.waiter, table_number=2)
        mock_notify.assert_not_called()

    @patch("apps.orders.services.notify_orders_changed")
    def test_adding_an_item_in_draft_does_not_notify(self, mock_notify):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        mock_notify.assert_not_called()

    @patch("apps.orders.services.notify_orders_changed")
    def test_sending_the_order_notifies(self, mock_notify):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        mock_notify.assert_called_once()

    @patch("apps.orders.services.notify_orders_changed")
    def test_adding_an_addition_does_not_notify_until_sent(self, mock_notify):
        """RF-5: an unsent addition is the waiter's own; the admin hears
        about it only when it is sent."""
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)
        mock_notify.reset_mock()
        services.add_item(self.order, name="Te", price=Decimal("3.00"))
        mock_notify.assert_not_called()
        services.send_additions(self.order, self.waiter)
        mock_notify.assert_called_once()

    @patch("apps.orders.services.notify_orders_changed")
    def test_voiding_an_item_notifies(self, mock_notify):
        item = services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.add_item(self.order, name="Te", price=Decimal("3.00"))
        services.send_order(self.order)
        mock_notify.reset_mock()
        services.void_item(self.order, item, self.waiter, "motivo")
        mock_notify.assert_called_once()

    @patch("apps.orders.services.notify_orders_changed")
    def test_voiding_the_whole_order_notifies(self, mock_notify):
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        mock_notify.reset_mock()
        services.void_order(self.order, self.admin, "motivo")
        mock_notify.assert_called_once()

    @patch("apps.orders.services.notify_orders_changed")
    def test_marking_delivered_does_not_notify(self, mock_notify):
        services.set_delivered(self.order, True)
        mock_notify.assert_not_called()

    @patch("apps.orders.services.notify_orders_changed")
    def test_releasing_the_table_does_not_notify(self, mock_notify):
        from apps.orders.models import Table

        table = Table.objects.get(number=1)
        table.status = Table.Status.PAID
        table.save(update_fields=["status"])
        mock_notify.reset_mock()
        services.release_table(table_number=1)
        mock_notify.assert_not_called()
