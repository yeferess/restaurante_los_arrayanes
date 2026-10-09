"""Builds the exact plain-text content of a kitchen ticket (plan.md,
section 3). Never reads a frozen/stored text — always derives the
content from the order's current state (RF-8, RF-10).
"""

import textwrap
import unicodedata

from django.conf import settings
from django.utils import timezone

from apps.kitchen_printing.models import PrintJob

TICKET_TYPE_LABELS = {
    PrintJob.TicketType.NEW_ORDER: "PEDIDO NUEVO",
    PrintJob.TicketType.ADDITION: "ADICION",
    PrintJob.TicketType.VOID: "ANULACION",
}


def to_ascii(text: str) -> str:
    """Strips accents/diacritics (á→a, ñ→n, ...) before anything reaches
    the printer — the Epson TM-U220 doesn't reliably support UTF-8
    (plan.md, decisión técnica 7)."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _columns() -> int:
    return settings.KITCHEN_PRINTER_COLUMNS


def _center(text: str, width: int) -> str:
    return text.center(width).rstrip()


def _build_header(job: PrintJob) -> list[str]:
    width = _columns()
    order = job.order
    label = TICKET_TYPE_LABELS[job.ticket_type]
    now = timezone.localtime().strftime("%d/%m/%y %H:%M")
    order_tag = f"Pedido #{order.id}"
    spacing = max(width - len(order_tag) - len(now), 1)

    return [
        "=" * width,
        _center(f"{label} - MESA {order.table_number}", width),
        "=" * width,
        f"{order_tag}{' ' * spacing}{now}",
        f"Mesero: {order.waiter.username}",
        "-" * width,
    ]


def format_item_line(quantity, name: str) -> list[str]:
    """Wraps one item line with a hanging indent so wrapped names stay
    aligned under the text, never cutting a word in half (RF-7)."""
    width = _columns()
    prefix = f"{quantity}x "
    indent = " " * len(prefix)
    wrapped = textwrap.wrap(name, width=max(width - len(prefix), 1))
    if not wrapped:
        return [prefix.rstrip()]
    lines = [prefix + wrapped[0]]
    lines.extend(indent + continuation for continuation in wrapped[1:])
    return lines


def build_notes_block(items) -> list[str]:
    """Notes grouped at the top of the ticket, one `*** NOTA ... ***`
    marker per item that has one — never repeated next to the item's
    own line further down (RF-6)."""
    width = _columns()
    lines: list[str] = []
    for item in items:
        if not item.note:
            continue
        marker = (
            f"*** NOTA ({to_ascii(item.name).upper()}): "
            f"{to_ascii(item.note).upper()} ***"
        )
        lines.extend(textwrap.wrap(marker, width=width, subsequent_indent="    "))
    return lines


def _since_reference(order):
    """RF-8: everything "new" for the next ticket is measured from the
    last time a ticket of this order actually reached paper — or from
    the very start if none ever did (covers the very first ticket,
    RF-3). Measured by id (strictly sequential) rather than by
    timestamp: two rows created in the same instant can tie on a
    timestamp but never on an auto-increment id."""
    last_printed = (
        PrintJob.objects.filter(order=order, status=PrintJob.Status.PRINTED)
        .order_by("-id")
        .first()
    )
    if last_printed is None:
        return 0, 0
    return last_printed.last_item_id or 0, last_printed.last_action_id or 0


def _pending_changes(order):
    from apps.orders.models import OrderAction

    last_item_id, last_action_id = _since_reference(order)
    added_items = list(order.items.filter(is_voided=False, id__gt=last_item_id))
    void_actions = list(
        OrderAction.objects.filter(
            order=order,
            action_type=OrderAction.ActionType.ITEM_VOIDED,
            id__gt=last_action_id,
            # An item added and voided within the same still-unprinted
            # window never reached paper in the first place, so there is
            # nothing to report as "voided" — it is omitted entirely
            # (RF-8). Only items that already made it onto a printed
            # ticket are worth announcing as voided now.
            item__id__lte=last_item_id,
        ).select_related("item")
    )
    return added_items, void_actions


def build_ticket_text(job: PrintJob) -> str:
    lines = _build_header(job)
    order = job.order

    added_items, void_actions = _pending_changes(order)
    voided_items = [action.item for action in void_actions if action.item is not None]
    show_section_labels = bool(added_items) and bool(void_actions)

    lines.extend(build_notes_block(added_items + voided_items))

    if added_items:
        if show_section_labels:
            lines.append("Agregado:")
        for item in added_items:
            lines.extend(format_item_line(item.quantity, to_ascii(item.name)))

    if void_actions:
        if show_section_labels:
            lines.append("Anulado:")
        for action in void_actions:
            item = action.item
            lines.extend(format_item_line(item.quantity, to_ascii(item.name)))
            lines.append(f"    Motivo: {to_ascii(action.reason or '')}")

    return "\n".join(lines)
