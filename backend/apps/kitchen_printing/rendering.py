"""Builds the exact plain-text content of a kitchen ticket (plan.md,
section 3). Never reads a frozen/stored text — always derives the
content from the order's current state (RF-8, RF-10).
"""

import textwrap
import unicodedata

from django.conf import settings
from django.utils import timezone

from apps.kitchen_printing.models import PrintJob
from apps.orders.models import table_label

TICKET_TYPE_LABELS = {
    PrintJob.TicketType.NEW_ORDER: "PEDIDO NUEVO",
    PrintJob.TicketType.ADDITION: "ADICION",
    PrintJob.TicketType.VOID: "ANULACION",
    PrintJob.TicketType.REPRINT: "REIMPRESION",
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


def _pack_line(left: str, right: str, width: int) -> str:
    spacing = max(width - len(left) - len(right), 1)
    return f"{left}{' ' * spacing}{right}"


def _build_header(order, label: str) -> list[str]:
    """RF-2, 003-RF-14: identifies the order by its daily number — never
    the internal id — alongside its send time; the print attempt's own
    time (already existing before RF-14) is a distinct field on the
    second line, never mixed up with the send time."""
    width = _columns()

    daily_number_tag = (
        f"N° {order.daily_number}" if order.daily_number is not None else "N°"
    )
    sent_at_tag = (
        f"Enviado {timezone.localtime(order.sent_at).strftime('%d/%m %H:%M')}"
        if order.sent_at is not None
        else "Enviado"
    )
    printed_at_tag = f"Impreso {timezone.localtime().strftime('%d/%m %H:%M')}"

    return [
        "=" * width,
        _center(f"{label} - {to_ascii(table_label(order)).upper()}", width),
        "=" * width,
        _pack_line(daily_number_tag, sent_at_tag, width),
        _pack_line(f"Mesero: {order.waiter.username}", printed_at_tag, width),
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


def format_note_lines(quantity, note: str) -> list[str]:
    """The item's note, right under its own line, as a
    `*** NOTA: ... ***` marker indented to align with the item's name
    (RF-6). Empty when the item has no note."""
    if not note:
        return []
    indent = " " * len(f"{quantity}x ")
    marker = f"*** NOTA: {to_ascii(note).upper()} ***"
    return textwrap.wrap(
        marker,
        width=_columns(),
        initial_indent=indent,
        subsequent_indent=indent,
    )


def format_item_with_note(item) -> list[str]:
    return format_item_line(item.quantity, to_ascii(item.name)) + format_note_lines(
        item.quantity, item.note
    )


def _since_reference(order):
    """RF-8: everything "new" for the next ticket is measured from the
    last time a ticket of this order actually reached paper — or from
    the very start if none ever did (covers the very first ticket,
    RF-3). Measured by id (strictly sequential) rather than by
    timestamp: two rows created in the same instant can tie on a
    timestamp but never on an auto-increment id. Reprints (RF-12) are
    copies on demand and never move this reference."""
    last_printed = (
        PrintJob.objects.filter(order=order, status=PrintJob.Status.PRINTED)
        .exclude(ticket_type=PrintJob.TicketType.REPRINT)
        .order_by("-id")
        .first()
    )
    if last_printed is None:
        return 0, 0
    return last_printed.last_item_id or 0, last_printed.last_action_id or 0


def pending_changes(order):
    """RF-8: what the next ticket would carry. Additions the waiter
    hasn't sent yet never count (003 RF-5) — but "Imprimir pedido" sends
    them right before printing."""
    from apps.orders.models import OrderAction
    from apps.orders.services import exclude_pending_send

    last_item_id, last_action_id = _since_reference(order)
    added_items = list(
        exclude_pending_send(order.items.filter(is_voided=False, id__gt=last_item_id))
    )
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


def has_unprinted_changes(order) -> bool:
    """RF-10: something of the order still has to reach paper — a ticket
    a failed attempt left pending, or sent changes never printed."""
    if order.print_jobs.filter(status=PrintJob.Status.PENDING).exists():
        return True
    added_items, void_actions = pending_changes(order)
    return bool(added_items or void_actions)


def build_ticket_text(job: PrintJob) -> str:
    order = job.order
    lines = _build_header(order, TICKET_TYPE_LABELS[job.ticket_type])

    added_items, void_actions = pending_changes(order)
    show_section_labels = bool(added_items) and bool(void_actions)

    if added_items:
        if show_section_labels:
            lines.append("Agregado:")
        for item in added_items:
            lines.extend(format_item_with_note(item))

    if void_actions:
        if show_section_labels:
            lines.append("Anulado:")
        for action in void_actions:
            lines.extend(format_item_with_note(action.item))
            lines.append(f"    Motivo: {to_ascii(action.reason or '')}")

    return "\n".join(lines)


def build_reprint_text(order) -> str:
    """RF-12: the whole order as it stands now — every active item with
    its note underneath — under a REIMPRESION header, so the kitchen
    knows it is a copy and not new work."""
    from apps.orders.services import exclude_pending_send

    lines = _build_header(order, TICKET_TYPE_LABELS[PrintJob.TicketType.REPRINT])
    for item in exclude_pending_send(order.items.filter(is_voided=False)).order_by("id"):
        lines.extend(format_item_with_note(item))
    return "\n".join(lines)
