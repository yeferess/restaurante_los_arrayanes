from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order, OrderAction, Table

User = get_user_model()

OCCUPIED_URL = "/api/mesas/ocupadas"


def _age(order, delta):
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - delta)
    order.refresh_from_db()
    return order


def _add_item(order):
    return services.add_item(order, name="Bandeja paisa", price=25000)


class DiscardStaleEmptyDraftsTests(TestCase):
    """RF-15 — empty drafts stop holding a table after EMPTY_DRAFT_TTL."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_stale", password="1234", role=User.Role.MESERO
        )

    def test_old_empty_draft_is_deleted_and_table_freed(self):
        order = _age(services.create_order(self.waiter, 1), timedelta(minutes=11))
        services.discard_stale_drafts()
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())
        self.assertEqual(Table.objects.get(number=1).status, Table.Status.FREE)

    def test_recent_empty_draft_is_kept(self):
        order = _age(services.create_order(self.waiter, 1), timedelta(minutes=5))
        services.discard_stale_drafts()
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        self.assertEqual(Table.objects.get(number=1).status, Table.Status.OCCUPIED)

    def test_old_draft_with_items_is_never_deleted(self):
        order = services.create_order(self.waiter, 1)
        _add_item(order)
        _age(order, timedelta(hours=5))
        services.discard_stale_drafts()
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())

    def test_sent_order_is_never_deleted(self):
        order = services.create_order(self.waiter, 1)
        _add_item(order)
        services.send_order(order)
        order.items.all().delete()
        _age(order, timedelta(hours=5))
        services.discard_stale_drafts()
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())

    def test_creating_on_a_table_held_by_an_old_empty_draft_succeeds(self):
        _age(services.create_order(self.waiter, 1), timedelta(minutes=11))
        other = User.objects.create_user(
            username="mesero_stale_2", password="1234", role=User.Role.MESERO
        )
        order = services.create_order(other, 1)
        self.assertEqual(order.waiter, other)


class DraftReminderTests(TestCase):
    """RF-15 — `draft_reminder` flags a draft with items left unsent."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_reminder", password="1234", role=User.Role.MESERO
        )
        self.order = services.create_order(self.waiter, 1)

    def test_old_draft_with_items_needs_reminder(self):
        _add_item(self.order)
        self.assertTrue(
            services.needs_draft_reminder(_age(self.order, timedelta(minutes=16)))
        )

    def test_recent_draft_does_not(self):
        _add_item(self.order)
        self.assertFalse(
            services.needs_draft_reminder(_age(self.order, timedelta(minutes=10)))
        )

    def test_empty_draft_does_not(self):
        self.assertFalse(
            services.needs_draft_reminder(_age(self.order, timedelta(minutes=16)))
        )

    def test_sent_order_does_not(self):
        _add_item(self.order)
        services.send_order(self.order)
        self.assertFalse(
            services.needs_draft_reminder(_age(self.order, timedelta(hours=1)))
        )


class MyOrdersDraftReminderViewTests(APITestCase):
    """RF-15 — the waiter's list exposes `draft_reminder` and no longer
    returns an expired empty draft."""

    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_mine_stale", password="1234", role=User.Role.MESERO
        )
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_mine_stale", "pin": "1234"}
        )

    def test_reminder_flag_and_expired_empty_draft(self):
        with_items = services.create_order(self.waiter, 1)
        _add_item(with_items)
        _age(with_items, timedelta(minutes=20))
        _age(services.create_order(self.waiter, 2), timedelta(minutes=20))

        response = self.client.get("/api/pedidos/mios")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([o["id"] for o in response.data], [with_items.id])
        self.assertTrue(response.data[0]["draft_reminder"])


class OccupiedTablesViewTests(APITestCase):
    """RF-15 — GET /api/mesas/ocupadas (admin-only)."""

    def setUp(self):
        services.resize_tables(4)
        self.admin = User.objects.create_user(
            username="admin_occupied", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="mesero_occupied", password="1234", role=User.Role.MESERO
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_occupied", "password": "Sup3rSecreta"},
        )

    def test_without_session_returns_401(self):
        response = self.client.get(OCCUPIED_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mesero_gets_403(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_occupied", "pin": "1234"}
        )
        response = self.client.get(OCCUPIED_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lists_occupied_tables_with_their_order_and_staleness(self):
        draft = services.create_order(self.waiter, 1)
        _add_item(draft)
        sent = services.create_order(self.waiter, 3)
        _add_item(sent)
        services.send_order(sent)
        _age(sent, timedelta(hours=4))
        _age(services.create_order(self.waiter, 4), timedelta(minutes=11))
        self._login_admin()

        response = self.client.get(OCCUPIED_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([t["number"] for t in response.data], [1, 3])
        first, third = response.data
        self.assertEqual(first["order"]["id"], draft.id)
        self.assertEqual(first["order"]["status"], "DRAFT")
        self.assertEqual(first["order"]["waiter_username"], "mesero_occupied")
        self.assertFalse(first["is_stale"])
        self.assertEqual(third["order"]["id"], sent.id)
        self.assertTrue(third["is_stale"])
        self.assertEqual(Table.objects.get(number=4).status, Table.Status.FREE)

    def test_admin_can_void_a_forgotten_draft(self):
        draft = services.create_order(self.waiter, 1)
        _add_item(draft)
        self._login_admin()

        response = self.client.post(
            f"/api/pedidos/{draft.id}/anular", {"reason": "borrador olvidado"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Table.objects.get(number=1).status, Table.Status.FREE)


class PreviousDayDraftsTests(TestCase):
    """RF-15 — no draft survives into a new local day, items or not."""

    def setUp(self):
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="mesero_prev_day", password="1234", role=User.Role.MESERO
        )

    def test_yesterdays_draft_with_items_is_deleted(self):
        order = services.create_order(self.waiter, 1)
        _add_item(order)
        _age(order, timedelta(days=1))
        services.discard_stale_drafts()
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())
        self.assertEqual(Table.objects.get(number=1).status, Table.Status.FREE)

    def test_todays_draft_with_items_is_kept(self):
        order = services.create_order(self.waiter, 1)
        _add_item(order)
        services.discard_stale_drafts()
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())

    def test_order_sent_yesterday_is_kept(self):
        order = services.create_order(self.waiter, 1)
        _add_item(order)
        services.send_order(order)
        _age(order, timedelta(days=1))
        services.discard_stale_drafts()
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())



class DiscardDraftViewTests(APITestCase):
    """RF-15 — POST /api/pedidos/{id}/eliminar-borrador: the admin frees a
    table held by a draft in one click, traced with a fixed reason."""

    def setUp(self):
        services.resize_tables(2)
        User.objects.create_user(
            username="admin_discard", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="mesero_discard", password="1234", role=User.Role.MESERO
        )
        self.draft = services.create_order(self.waiter, 1)
        _add_item(self.draft)

    def _url(self, order):
        return f"/api/pedidos/{order.id}/eliminar-borrador"

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_discard", "password": "Sup3rSecreta"},
        )

    def test_admin_discards_a_draft_and_the_action_is_traced(self):
        self._login_admin()
        response = self.client.post(self._url(self.draft))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, Order.Status.VOIDED)
        self.assertEqual(Table.objects.get(number=1).status, Table.Status.FREE)
        action = OrderAction.objects.get(order=self.draft)
        self.assertEqual(action.action_type, OrderAction.ActionType.ORDER_VOIDED)
        self.assertEqual(action.performed_by.username, "admin_discard")
        self.assertEqual(action.reason, services.DRAFT_DISCARD_REASON)

    def test_sent_order_returns_409(self):
        services.send_order(self.draft)
        self._login_admin()
        response = self.client.post(self._url(self.draft))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, Order.Status.IN_PROGRESS)

    def test_mesero_gets_403(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_discard", "pin": "1234"}
        )
        response = self.client.post(self._url(self.draft))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_order_returns_404(self):
        self._login_admin()
        response = self.client.post("/api/pedidos/999999/eliminar-borrador")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_without_session_returns_401(self):
        response = self.client.post(self._url(self.draft))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
