"""T97 — "Crear pedido" y "Imprimir pedido" son pasos separados
(003 RF-5, 004 RF-1).

- Crear el pedido lo deja en el sistema (el admin lo ve) sin imprimir.
- Una adición queda "sin enviar": solo la ve el mesero, no cuenta en el
  total ni se cobra, hasta que la envía ("Enviar adición") o imprime.
- "Imprimir pedido" saca un solo ticket con todo lo que falta en papel.
- Las anulaciones esperan al siguiente "Imprimir pedido".
"""

from decimal import Decimal
from importlib import import_module
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing import services as printing
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.models import PrintJob
from apps.orders import services
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentAccount
from apps.payments.services import charge_order

User = get_user_model()


class _Fixture(TestCase):
    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_aparte", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="otro_mesero", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_aparte", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.printer = FakePrinterAdapter()
        patcher = patch(
            "apps.kitchen_printing.services.get_printer_adapter",
            side_effect=lambda: self.printer,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.order = services.create_order(self.waiter, table_number=1)
        self.bandeja = services.add_item(
            self.order, name="Bandeja paisa", price=Decimal("25000")
        )
        services.send_order(self.order)

        self.waiter_client = APIClient()
        self.waiter_client.force_authenticate(self.waiter)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

    def _print(self):
        return self.waiter_client.post(f"/api/pedidos/{self.order.id}/imprimir")

    def _detail(self, client):
        return client.get(f"/api/pedidos/{self.order.id}").data


class CreateWithoutPrintingTests(_Fixture):
    def test_creating_the_order_does_not_print_but_the_admin_sees_it(self):
        self.assertEqual(self.printer.printed_texts, [])
        incoming = self.admin_client.get("/api/pedidos/entrantes").data
        self.assertEqual([o["id"] for o in incoming], [self.order.id])
        self.assertTrue(self._detail(self.waiter_client)["has_unprinted_changes"])

    def test_the_first_print_is_a_new_order_ticket_with_every_item(self):
        response = self._print()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["print_warning"])
        self.assertEqual(len(self.printer.printed_texts), 1)
        self.assertIn("PEDIDO NUEVO", self.printer.printed_texts[0])
        self.assertIn("Bandeja paisa", self.printer.printed_texts[0])
        self.assertFalse(response.data["has_unprinted_changes"])

    def test_printing_with_nothing_new_is_refused(self):
        self._print()
        response = self._print()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.printer.printed_texts), 1)

    def test_an_order_never_printed_is_not_marked_as_a_print_failure(self):
        """Lo de vitrina: el mesero no imprime y el admin no ve ningún
        "No impreso en cocina"."""
        incoming = self.admin_client.get("/api/pedidos/entrantes").data
        self.assertFalse(incoming[0]["has_pending_print"])


class UnsentAdditionsTests(_Fixture):
    def setUp(self):
        super().setUp()
        self._print()
        self.jugo = services.add_item(self.order, name="Jugo de mora", price=Decimal("6000"))
        self.tinto = services.add_item(self.order, name="Tinto", price=Decimal("2000"))

    def test_two_additions_then_print_make_a_single_addition_ticket(self):
        response = self._print()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.printer.printed_texts), 2)
        ticket = self.printer.printed_texts[1]
        self.assertIn("ADICION", ticket)
        self.assertIn("Jugo de mora", ticket)
        self.assertIn("Tinto", ticket)
        self.assertNotIn("Bandeja paisa", ticket)
        self.assertEqual(
            PrintJob.objects.filter(ticket_type=PrintJob.TicketType.ADDITION).count(), 1
        )
        self.assertEqual(response.data["pending_additions_count"], 0)

    def test_adding_does_not_print(self):
        self.assertEqual(len(self.printer.printed_texts), 1)

    def test_the_admin_does_not_see_an_unsent_addition(self):
        admin_view = self._detail(self.admin_client)
        self.assertEqual([i["name"] for i in admin_view["items"]], ["Bandeja paisa"])
        self.assertEqual(admin_view["total"], Decimal("25000"))
        self.assertNotIn("pending_additions_count", admin_view)

        incoming = self.admin_client.get("/api/pedidos/entrantes").data
        self.assertEqual([i["name"] for i in incoming[0]["items"]], ["Bandeja paisa"])

        preview = self.admin_client.post(
            f"/api/pedidos/{self.order.id}/cobro/previsualizar", {}, format="json"
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(Decimal(preview.data["subtotal"]), Decimal("25000"))

    def test_the_waiter_sees_it_flagged_and_out_of_the_total(self):
        mine = self._detail(self.waiter_client)
        flags = {i["name"]: i["pending_send"] for i in mine["items"]}
        self.assertEqual(
            flags, {"Bandeja paisa": False, "Jugo de mora": True, "Tinto": True}
        )
        self.assertEqual(mine["total"], Decimal("25000"))
        self.assertEqual(mine["pending_additions_count"], 2)
        self.assertEqual(mine["pending_additions_total"], "8000.00")
        self.assertTrue(mine["has_unprinted_changes"])

    def test_sending_shows_it_to_the_admin_without_printing(self):
        response = self.waiter_client.post(
            f"/api/pedidos/{self.order.id}/enviar-adicion"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pending_additions_count"], 0)
        self.assertEqual(len(self.printer.printed_texts), 1)

        admin_view = self._detail(self.admin_client)
        self.assertEqual(
            [i["name"] for i in admin_view["items"]],
            ["Bandeja paisa", "Jugo de mora", "Tinto"],
        )
        self.assertEqual(admin_view["total"], Decimal("33000"))
        # Enviada pero sin imprimir: "Imprimir pedido" la saca después.
        self.assertTrue(response.data["has_unprinted_changes"])

    def test_sending_with_nothing_pending_is_refused(self):
        self.waiter_client.post(f"/api/pedidos/{self.order.id}/enviar-adicion")
        response = self.waiter_client.post(
            f"/api/pedidos/{self.order.id}/enviar-adicion"
        )
        self.assertEqual(response.status_code, 409)

    def test_only_the_owner_can_send_or_print(self):
        other = APIClient()
        other.force_authenticate(self.other_waiter)
        self.assertEqual(
            other.post(f"/api/pedidos/{self.order.id}/enviar-adicion").status_code, 403
        )
        self.assertEqual(
            other.post(f"/api/pedidos/{self.order.id}/imprimir").status_code, 403
        )
        with self.assertRaises(ValidationError):
            services.send_additions(self.order, self.other_waiter)

    def test_an_unsent_addition_can_be_removed_without_a_reason(self):
        response = self.waiter_client.delete(
            f"/api/pedidos/{self.order.id}/items/{self.jugo.id}"
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(OrderItem.objects.filter(pk=self.jugo.pk).exists())

    def test_a_sent_item_still_cannot_be_removed(self):
        response = self.waiter_client.delete(
            f"/api/pedidos/{self.order.id}/items/{self.bandeja.id}"
        )
        self.assertEqual(response.status_code, 409)

    def test_an_unsent_addition_cannot_be_voided(self):
        with self.assertRaises(ValidationError):
            services.void_item(self.order, self.jugo, self.waiter, "motivo")

    def test_charging_ignores_and_drops_unsent_additions(self):
        account = PaymentAccount.objects.get(name="Efectivo")
        payment = charge_order(self.order, self.admin, account)
        self.assertEqual(payment.amount, Decimal("25000"))
        self.assertFalse(
            OrderItem.objects.filter(pk__in=[self.jugo.pk, self.tinto.pk]).exists()
        )

    def test_voiding_the_whole_order_drops_unsent_additions(self):
        services.void_order(self.order, self.admin, "cliente se fue")
        self.assertEqual(self.order.items.count(), 1)

    def test_closed_orders_cannot_send_or_print(self):
        account = PaymentAccount.objects.get(name="Efectivo")
        charge_order(self.order, self.admin, account)
        self.assertEqual(self._print().status_code, 409)
        self.assertEqual(
            self.waiter_client.post(
                f"/api/pedidos/{self.order.id}/enviar-adicion"
            ).status_code,
            409,
        )


class VoidsWaitForPrintTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.limonada = services.add_item(
            self.order, name="Limonada", price=Decimal("5000")
        )
        services.send_additions(self.order, self.waiter)
        self._print()

    def test_a_void_does_not_print_and_comes_out_on_the_next_print(self):
        services.void_item(self.order, self.limonada, self.waiter, "no quiso")
        self.assertEqual(len(self.printer.printed_texts), 1)
        self.assertTrue(self._detail(self.waiter_client)["has_unprinted_changes"])

        self._print()
        ticket = self.printer.printed_texts[1]
        self.assertIn("ANULACION", ticket)
        self.assertIn("Limonada", ticket)
        self.assertIn("Motivo: no quiso", ticket)

    def test_a_void_and_an_addition_share_one_ticket(self):
        services.void_item(self.order, self.limonada, self.waiter, "no quiso")
        services.add_item(self.order, name="Gaseosa", price=Decimal("4000"))
        self._print()
        self.assertEqual(len(self.printer.printed_texts), 2)
        ticket = self.printer.printed_texts[1]
        self.assertIn("ADICION", ticket)
        self.assertIn("Agregado:", ticket)
        self.assertIn("Gaseosa", ticket)
        self.assertIn("Anulado:", ticket)
        self.assertIn("Limonada", ticket)

    def test_a_void_never_drags_an_unsent_addition_onto_paper(self):
        services.add_item(self.order, name="Gaseosa", price=Decimal("4000"))
        services.void_item(self.order, self.limonada, self.waiter, "no quiso")
        # Imprimir sí envía la adición: ambas salen juntas. Lo que importa
        # es que anular, por sí solo, no la mandó a ningún lado.
        self.assertEqual(len(self.printer.printed_texts), 1)
        admin_view = self._detail(self.admin_client)
        self.assertNotIn("Gaseosa", [i["name"] for i in admin_view["items"]])


class BackfillMigrationTests(TestCase):
    """La migración 0007 marca como enviados los ítems de pedidos que ya
    no eran borrador, para que nada viejo aparezca "Sin enviar"."""

    def test_existing_lines_of_sent_orders_are_marked_as_sent(self):
        services.resize_tables(2)
        waiter = User.objects.create_user(
            username="mig_w", password="1234", role=User.Role.MESERO
        )
        sent = services.create_order(waiter, table_number=1)
        services.add_item(sent, name="Arepa", price=Decimal("3000"))
        services.send_order(sent)
        addition = services.add_item(sent, name="Tinto", price=Decimal("2000"))
        draft = services.create_order(waiter, table_number=2)
        draft_item = services.add_item(draft, name="Sopa", price=Decimal("9000"))
        OrderItem.objects.update(sent_at=None)

        migration = import_module("apps.orders.migrations.0007_orderitem_sent_at")
        migration.mark_existing_items_as_sent(django_apps, None)

        addition.refresh_from_db()
        draft_item.refresh_from_db()
        sent.refresh_from_db()
        self.assertEqual(addition.sent_at, sent.sent_at)
        self.assertIsNone(draft_item.sent_at)
        self.assertEqual(Order.objects.get(pk=sent.pk).status, Order.Status.IN_PROGRESS)
