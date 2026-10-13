"""Orchestrates consolidation, the synchronous print attempt, and the
owner-only manual retry (plan.md, sección 5; RF-1, RF-8, RF-9, RF-10,
RF-11).
"""

import threading

from django.core.exceptions import ValidationError
from django.db.models import Max
from django.utils import timezone

from apps.kitchen_printing.adapters import PrinterFailureError, PrinterNotDetectedError
from apps.kitchen_printing.factory import get_printer_adapter
from apps.kitchen_printing.models import PrintJob
from apps.kitchen_printing.rendering import (
    build_reprint_text,
    build_ticket_text,
    has_unprinted_changes,
    pending_changes,
)
from apps.orders.models import Order, OrderAction
from apps.orders.services import (
    exclude_pending_send,
    notify_orders_changed,
    pending_additions,
    send_additions,
)

PRINTER_NOT_DETECTED_MESSAGE = "Impresora de cocina no detectada."
PRINTER_FAILURE_MESSAGE = "Error al imprimir el ticket de cocina."

# A single physical printer: only one print job may reach the adapter
# at a time, process-wide (plan.md, decisión técnica — lock en memoria
# vs. cola externa; constitution regla 1).
_print_lock = threading.Lock()


def _attempt_print(job, created):
    """Assumes `_print_lock` is already held by the caller — every read
    and write this function does to `PrintJob`/`OrderAction` rows is
    serialized under that same single lock, not just the physical call
    to the adapter. A single physical printer gives up nothing in
    throughput by also serializing this bookkeeping, and it closes a
    real race window: two threads writing to the same SQLite table at
    once can collide (observed as `OperationalError: database table is
    locked` under the shared-cache in-memory test database — SQLite's
    busy-timeout retry does not apply to that specific lock kind)."""
    if not created:
        job.attempts += 1
        job.save(update_fields=["attempts"])

    order = job.order
    text = build_ticket_text(job)
    adapter = get_printer_adapter()
    try:
        adapter.print_ticket(text)
    except PrinterNotDetectedError:
        return PRINTER_NOT_DETECTED_MESSAGE
    except PrinterFailureError:
        return PRINTER_FAILURE_MESSAGE

    job.status = PrintJob.Status.PRINTED
    job.printed_at = timezone.now()
    job.last_item_id = (
        exclude_pending_send(order.items).aggregate(Max("id"))["id__max"] or 0
    )
    job.last_action_id = (
        OrderAction.objects.filter(
            order=order, action_type=OrderAction.ActionType.ITEM_VOIDED
        ).aggregate(Max("id"))["id__max"]
        or 0
    )
    job.save(
        update_fields=["status", "printed_at", "last_item_id", "last_action_id"]
    )
    return None


def register_event_and_print(order, event_type):
    """RF-1, RF-8, RF-9: reuse the order's single pending ticket if one
    already exists (consolidation — its header stays fixed to whichever
    event created it); otherwise open a new one. Either way, attempt to
    print it now, synchronously.

    Notifies again once the attempt is over: callers already notified
    before printing, and a screen that refetched in between saw the job
    still PENDING — without this second notification it would keep
    showing "No impreso en cocina" for a ticket that did print."""
    with _print_lock:
        pending = order.print_jobs.filter(status=PrintJob.Status.PENDING).first()
        created = pending is None
        job = pending or PrintJob.objects.create(order=order, ticket_type=event_type)
        print_warning = _attempt_print(job, created)
    notify_orders_changed()
    return print_warning


def _ticket_type_for(order):
    """RF-1: the header of a new ticket — PEDIDO NUEVO until something of
    the order reached paper, then ADICION (with anything added) or
    ANULACION (only voids). A ticket a failed attempt left pending keeps
    its own header (RF-8)."""
    ever_printed = (
        order.print_jobs.filter(status=PrintJob.Status.PRINTED)
        .exclude(ticket_type=PrintJob.TicketType.REPRINT)
        .exists()
    )
    if not ever_printed:
        return PrintJob.TicketType.NEW_ORDER
    added_items, _ = pending_changes(order)
    return PrintJob.TicketType.ADDITION if added_items else PrintJob.TicketType.VOID


def print_order(order, waiter):
    """RF-1, RF-9, RF-10, RF-11: "Imprimir pedido" — the only way a kitchen
    ticket gets printed. Exclusive to the order's own waiter while it is
    in progress. Sends the additions still pending first (one tap for
    the kitchen), then prints in a single ticket everything that hasn't
    reached paper yet — or retries the ticket a failed attempt left
    pending."""
    if order.waiter_id != waiter.id:
        raise ValidationError(
            "Solo el mesero dueño del pedido puede imprimirlo.",
            code="not_owner",
        )
    if order.status != Order.Status.IN_PROGRESS:
        raise ValidationError(
            "Este pedido ya no se puede imprimir.", code="not_editable"
        )

    if pending_additions(order).exists():
        send_additions(order, waiter)
    if not has_unprinted_changes(order):
        raise ValidationError(
            "No hay nada nuevo para imprimir en este pedido.",
            code="nothing_to_print",
        )
    return register_event_and_print(order, _ticket_type_for(order))


def retry_print(order, waiter):
    """RF-10: the old "Reintentar" — kept as an alias so nothing calling
    it breaks; "Imprimir pedido" covers the retry too."""
    return print_order(order, waiter)


def reprint_order(order, user):
    """RF-12: print a copy of the whole order on demand. The order's own
    waiter can do it while the order is still open; an admin also after
    it was charged (the "Cobrados" tab, 005). Never touches the order's
    pending ticket, if any, nor the "already on paper" reference.

    Only a copy that actually reached paper is recorded; a failed one
    just returns the warning, so it never shows up as "No impreso"."""
    is_admin = user.role == user.Role.ADMIN
    if not is_admin and order.waiter_id != user.id:
        raise ValidationError(
            "Solo el mesero dueño del pedido o un admin pueden reimprimirlo.",
            code="not_owner",
        )
    allowed_statuses = (
        (Order.Status.IN_PROGRESS, Order.Status.CHARGED)
        if is_admin
        else (Order.Status.IN_PROGRESS,)
    )
    if order.status not in allowed_statuses:
        raise ValidationError(
            "Este pedido no se puede reimprimir.", code="not_editable"
        )

    with _print_lock:
        try:
            get_printer_adapter().print_ticket(build_reprint_text(order))
        except PrinterNotDetectedError:
            return PRINTER_NOT_DETECTED_MESSAGE
        except PrinterFailureError:
            return PRINTER_FAILURE_MESSAGE
        PrintJob.objects.create(
            order=order,
            ticket_type=PrintJob.TicketType.REPRINT,
            status=PrintJob.Status.PRINTED,
            printed_at=timezone.now(),
        )
    return None
