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
from apps.kitchen_printing.rendering import build_ticket_text
from apps.orders.models import Order, OrderAction
from apps.orders.services import notify_orders_changed

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
    job.last_item_id = order.items.aggregate(Max("id"))["id__max"] or 0
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


def retry_print(order, waiter):
    """RF-9, RF-10, RF-11: manual retry, exclusive to the order's own
    waiter, blocked once the order is charged or voided."""
    if order.waiter_id != waiter.id:
        raise ValidationError(
            "Solo el mesero dueño del pedido puede reintentar la impresión.",
            code="not_owner",
        )
    if order.status in (Order.Status.CHARGED, Order.Status.VOIDED):
        raise ValidationError(
            "Este pedido ya no admite reintentos de impresión.",
            code="not_editable",
        )

    job = order.print_jobs.filter(status=PrintJob.Status.PENDING).first()
    if job is None:
        raise ValidationError(
            "Este pedido no tiene ningún ticket pendiente de impresión.",
            code="not_found",
        )

    with _print_lock:
        print_warning = _attempt_print(job, created=False)
    if print_warning is None:
        notify_orders_changed()
    return print_warning
