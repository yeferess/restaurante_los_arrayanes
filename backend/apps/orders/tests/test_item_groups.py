"""T100 — 003 RF-3: the same item shows summed into one line on screens
and on the bill and receipt (005 RF-11, RF-13), even when part of it is
a later addition; underneath each part stays its own line, so the
kitchen still gets only the addition."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.services import print_order
from apps.menu.models import Category, Product
from apps.orders import services
from apps.orders.grouping import group_items
from apps.orders.models import OrderItem
from apps.payments import services as payment_services
from apps.payments.models import Payment, PaymentAccount
from apps.payments.receipt import build_bill_text, build_receipt_text

User = get_user_model()


class _Fixture(TestCase):
    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="waiter_groups", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_groups", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        category = Category.objects.create(name="Platos")
        self.bandeja = Product.objects.create(
            name="Bandeja paisa", category=category, price=Decimal("25000")
        )
        self.ajiaco = Product.objects.create(
            name="Ajiaco", category=category, price=Decimal("20000")
        )
        self.printer = FakePrinterAdapter()
        for target in (
            "apps.kitchen_printing.services.get_printer_adapter",
            "apps.payments.services.get_printer_adapter",
        ):
            patcher = patch(target, side_effect=lambda: self.printer)
            patcher.start()
            self.addCleanup(patcher.stop)

        # 2x Bandeja paisa + 1x Ajiaco sent; then 1x Bandeja paisa added.
        self.original = self._add(self.bandeja, quantity=2, note="una sin chorizo")
        self._add(self.ajiaco)
        services.send_order(self.order)
        self.addition = self._add(self.bandeja, note="sin frijoles")

    def _add(self, product, quantity=1, note=""):
        return services.add_item(
            self.order, product_id=product.pk, quantity=quantity, note=note
        )

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class GroupItemsTests(_Fixture):
    def test_sent_line_and_addition_of_the_same_item_are_summed(self):
        groups = group_items(self.order.items.all())
        self.assertEqual(
            [(group.name, group.quantity) for group in groups],
            [("Bandeja paisa", 3), ("Ajiaco", 1)],
        )
        bandeja = groups[0]
        self.assertEqual(bandeja.line_total, Decimal("75000"))
        self.assertEqual(bandeja.note, "una sin chorizo\nsin frijoles")
        self.assertEqual([part.id for part in bandeja.parts], [self.original.id, self.addition.id])

    def test_another_price_stays_apart(self):
        self.bandeja.price = Decimal("27000")
        self.bandeja.save()
        self._add(self.bandeja)
        groups = group_items(self.order.items.all())
        self.assertEqual([group.quantity for group in groups], [3, 1, 1])

    def test_off_menu_item_never_joins_a_catalog_product(self):
        services.add_item(self.order, name="Bandeja paisa", price=Decimal("25000"))
        groups = group_items(self.order.items.all())
        self.assertEqual(len(groups), 3)

    def test_voided_lines_are_left_out(self):
        services.send_additions(self.order, self.waiter)
        services.void_item(self.order, self.original, self.waiter, "error")
        groups = group_items(self.order.items.all())
        self.assertEqual(groups[0].name, "Ajiaco")
        self.assertEqual(groups[1].quantity, 1)


class SerializerTests(_Fixture):
    def test_waiter_sees_the_summed_line_with_its_parts(self):
        data = self._client(self.waiter).get(f"/api/pedidos/{self.order.id}").data
        bandeja = data["item_groups"][0]
        self.assertEqual(bandeja["quantity"], 3)
        self.assertEqual(bandeja["line_total"], "75000.00")
        self.assertEqual(bandeja["note"], "una sin chorizo\nsin frijoles")
        self.assertEqual(
            [(part["item_id"], part["line_type"], part["pending_send"]) for part in bandeja["parts"]],
            [
                (self.original.id, OrderItem.LineType.ORIGINAL, False),
                (self.addition.id, OrderItem.LineType.ADDITION, True),
            ],
        )
        # The lines themselves are untouched.
        self.assertEqual(len(data["items"]), 3)

    def test_admin_never_sees_the_unsent_part(self):
        incoming = self._client(self.admin).get("/api/pedidos/entrantes").data
        bandeja = incoming[0]["item_groups"][0]
        self.assertEqual(bandeja["quantity"], 2)
        self.assertEqual(len(bandeja["parts"]), 1)

    def test_admin_sees_the_sum_once_the_addition_is_sent(self):
        services.send_additions(self.order, self.waiter)
        incoming = self._client(self.admin).get("/api/pedidos/entrantes").data
        self.assertEqual(incoming[0]["item_groups"][0]["quantity"], 3)


class PrintedTicketsTests(_Fixture):
    def setUp(self):
        super().setUp()
        services.send_additions(self.order, self.waiter)

    def test_bill_shows_the_summed_line(self):
        text = build_bill_text(self.order, payment_services.preview_charge(self.order))
        self.assertIn("3x Bandeja paisa", text)
        self.assertRegex(text, r"3 x 25\.000\s+75\.000")
        self.assertNotIn("2x Bandeja paisa", text)

    def test_receipt_shows_the_summed_line(self):
        account = PaymentAccount.objects.get(name="Efectivo")
        payment_services.charge_order(self.order, self.admin, account)
        payment = Payment.objects.get(order=self.order)
        text = build_receipt_text(self.order, payment)
        self.assertIn("3x Bandeja paisa", text)
        self.assertRegex(text, r"TOTAL\s+95\.000")

    def test_kitchen_addition_ticket_still_shows_only_the_addition(self):
        print_order(self.order, self.waiter)
        self._add(self.bandeja)
        print_order(self.order, self.waiter)
        addition_ticket = self.printer.printed_texts[-1]
        self.assertIn("ADICION", addition_ticket)
        self.assertIn("1x Bandeja paisa", addition_ticket)
        self.assertNotIn("4x", addition_ticket)
        self.assertNotIn("Ajiaco", addition_ticket)
