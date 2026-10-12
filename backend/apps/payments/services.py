"""Catalog of payment options and the charge/void-charge flow (plan.md,
sección 5; RF-1 a RF-7).
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.kitchen_printing.adapters import PrinterFailureError, PrinterNotDetectedError
from apps.kitchen_printing.factory import get_printer_adapter
from apps.kitchen_printing.services import (
    PRINTER_FAILURE_MESSAGE,
    PRINTER_NOT_DETECTED_MESSAGE,
    _print_lock,
)
from apps.orders.models import Order, OrderAction, Table
from apps.orders.services import notify_orders_changed, register_action
from apps.payments.models import Payment, PaymentAccount
from apps.payments.receipt import build_receipt_text

DISCOUNT_REASON_MAX_LENGTH = 200


def create_account(name):
    """RF-2: add a new account to the catalog. Names are unique and
    immutable once created — "Efectivo" itself is never created here,
    it is seeded by a migration."""
    name = (name or "").strip()
    if not name:
        raise ValidationError(
            "El nombre de la cuenta no puede estar vacío.", code="invalid"
        )
    if PaymentAccount.objects.filter(name=name).exists():
        raise ValidationError(
            "Ya existe una cuenta con ese nombre.", code="duplicate"
        )
    return PaymentAccount.objects.create(name=name)


def _active_items_total(order):
    return sum(
        (item.unit_price * item.quantity for item in order.items.all() if not item.is_voided),
        Decimal("0.00"),
    )


def _parse_discount(raw):
    if raw in (None, ""):
        return Decimal("0.00")
    try:
        discount = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise ValidationError("El descuento debe ser un valor numérico.", code="invalid")
    if not discount.is_finite():
        raise ValidationError("El descuento debe ser un valor numérico.", code="invalid")
    return discount


def _ensure_chargeable(order):
    try:
        table = Table.objects.get(number=order.table_number)
    except Table.DoesNotExist:
        table = None
    if order.status != Order.Status.IN_PROGRESS or table is None or (
        table.status != Table.Status.OCCUPIED
    ):
        raise ValidationError(
            "Este pedido no admite cobro en este momento.", code="not_chargeable"
        )
    return table


def compute_charge(order, raw_discount=None):
    """RF-10: subtotal of the active items, the optional peso discount
    and the total to pay. The single place where the discount is
    validated — used by both the preview and the charge itself."""
    subtotal = _active_items_total(order)
    discount = _parse_discount(raw_discount)
    if discount < 0:
        raise ValidationError("El descuento no puede ser negativo.", code="invalid")
    if discount > subtotal:
        raise ValidationError(
            "El descuento no puede ser mayor que el total del pedido.", code="invalid"
        )
    return {"subtotal": subtotal, "discount": discount, "total": subtotal - discount}


def preview_charge(order, raw_discount=None):
    """RF-10: what charging with this discount would produce — saves
    nothing."""
    _ensure_chargeable(order)
    return compute_charge(order, raw_discount)


def charge_order(order, admin, account, discount=None, discount_reason=""):
    """RF-1, RF-3, RF-4, RF-5, RF-10: charge the order of an occupied
    table with the chosen payment option and an optional peso discount.
    The DB's own `unique_active_payment_per_order` constraint
    (apps.payments.models) rejects a concurrent double-charge instead of
    an application-level lock (plan.md, sección 4)."""
    table = _ensure_chargeable(order)
    amounts = compute_charge(order, discount)
    reason = (discount_reason or "").strip()[:DISCOUNT_REASON_MAX_LENGTH]
    if amounts["discount"] == 0:
        reason = ""

    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                order=order,
                account=account,
                subtotal=amounts["subtotal"],
                discount=amounts["discount"],
                discount_reason=reason,
                amount=amounts["total"],
                charged_by=admin,
            )
    except IntegrityError:
        raise ValidationError("Este pedido ya fue cobrado.", code="already_charged")

    order.status = Order.Status.CHARGED
    order.save(update_fields=["status"])
    table.status = Table.Status.PAID
    table.save(update_fields=["status"])
    register_action(order, OrderAction.ActionType.CHARGED, admin)
    return payment


def print_receipt(order):
    """RF-11: print the customer receipt of a charged order on the same
    printer as the kitchen, under the same lock so both never interleave.
    Not a kitchen PrintJob — nothing is stored. Returns a printer
    warning, or None when it printed."""
    payment = Payment.objects.filter(order=order, status=Payment.Status.ACTIVE).first()
    if order.status != Order.Status.CHARGED or payment is None:
        raise ValidationError(
            "Solo se puede imprimir el comprobante de un pedido cobrado.",
            code="not_charged",
        )
    text = build_receipt_text(order, payment)
    with _print_lock:
        try:
            get_printer_adapter().print_ticket(text, doc_name="Comprobante")
        except PrinterNotDetectedError:
            return PRINTER_NOT_DETECTED_MESSAGE
        except PrinterFailureError:
            return PRINTER_FAILURE_MESSAGE
    return None


def void_charge(order, admin, reason):
    """RF-6: correct an erroneous charge by voiding it — never editing
    or deleting the original `Payment` row. Blocked if the table was
    already reassigned to a different active order, to protect 003
    RF-2's invariant (a table has at most one active order)."""
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("El motivo es obligatorio.", code="invalid")

    payment = Payment.objects.filter(order=order, status=Payment.Status.ACTIVE).first()
    if payment is None:
        if Payment.objects.filter(order=order).exists():
            raise ValidationError(
                "El cobro de este pedido ya fue anulado.", code="already_voided"
            )
        raise ValidationError(
            "Este pedido no tiene ningún cobro activo.", code="not_found"
        )

    table_reassigned = (
        Order.objects.filter(
            table_number=order.table_number,
            status__in=(Order.Status.DRAFT, Order.Status.IN_PROGRESS),
        )
        .exclude(pk=order.pk)
        .exists()
    )
    if table_reassigned:
        raise ValidationError(
            "La mesa ya tiene un pedido nuevo; no se puede anular este cobro.",
            code="table_reassigned",
        )

    payment.status = Payment.Status.VOIDED
    payment.voided_by = admin
    payment.voided_at = timezone.now()
    payment.void_reason = reason
    payment.save(update_fields=["status", "voided_by", "voided_at", "void_reason"])

    order.status = Order.Status.IN_PROGRESS
    order.save(update_fields=["status"])

    try:
        table = Table.objects.get(number=order.table_number)
    except Table.DoesNotExist:
        table = None
    if table is not None and table.status == Table.Status.PAID:
        table.status = Table.Status.OCCUPIED
        table.save(update_fields=["status"])

    notify_orders_changed()
    return order


def delete_account(account):
    """RF-2: remove an account, but only while it has never been used
    by any payment (active or voided), and never the fixed "Efectivo"
    account."""
    if account.is_fixed:
        raise ValidationError(
            "No se puede eliminar la cuenta 'Efectivo'.", code="fixed"
        )
    if Payment.objects.filter(account=account).exists():
        raise ValidationError(
            "Esta cuenta ya se usó en un cobro y no se puede eliminar.",
            code="in_use",
        )
    account.delete()
