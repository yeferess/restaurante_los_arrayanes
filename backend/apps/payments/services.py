"""Catalog of payment options and the charge/void-charge flow (plan.md,
sección 5; RF-1 a RF-7).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders.models import Order, OrderAction, Table
from apps.orders.services import notify_orders_changed, register_action
from apps.payments.models import Payment, PaymentAccount


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


def charge_order(order, admin, account):
    """RF-1, RF-3, RF-4, RF-5: charge the order of an occupied table
    with the chosen payment option. The DB's own
    `unique_active_payment_per_order` constraint (apps.payments.models)
    rejects a concurrent double-charge instead of an application-level
    lock (plan.md, sección 4)."""
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

    amount = _active_items_total(order)

    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                order=order, account=account, amount=amount, charged_by=admin
            )
    except IntegrityError:
        raise ValidationError("Este pedido ya fue cobrado.", code="already_charged")

    order.status = Order.Status.CHARGED
    order.save(update_fields=["status"])
    table.status = Table.Status.PAID
    table.save(update_fields=["status"])
    register_action(order, OrderAction.ActionType.CHARGED, admin)
    return payment


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
