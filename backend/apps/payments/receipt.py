"""Plain-text customer receipt of a charged order (005-cobro RF-11),
and the bill printed before paying (RF-13) with the same layout.

Printed on the same Epson TM-U220 as the kitchen tickets, so it reuses
their 40-column, ASCII-only layout helpers. Deliberately leaves out the
admin's note (003 RF-17) and the per-dish kitchen notes.
"""

import textwrap
from decimal import Decimal

from django.utils import timezone

from apps.kitchen_printing.rendering import _center, _columns, _pack_line, to_ascii
from apps.orders.models import table_label

RECEIPT_TITLE = "FINCA DE RECREO LOS ARRAYANES"
RECEIPT_SUBTITLE = "COMPROBANTE"
RECEIPT_FOOTER = "Gracias por su visita"
BILL_SUBTITLE = "CUENTA"
BILL_FOOTER = "No es comprobante de pago"


def format_pesos(value) -> str:
    """Colombian thousands separator; cents only when there are any
    (ej. 50000 -> "50.000", 1234.5 -> "1.234,50")."""
    value = Decimal(value)
    if value == value.to_integral_value():
        return f"{int(value):,}".replace(",", ".")
    integer, cents = f"{value:,.2f}".split(".")
    return f"{integer.replace(',', '.')},{cents}"


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width) or [""]


def _header_and_items(order, subtitle, moment, width) -> list[str]:
    """Title, order number, place and time, then every active item with
    its quantity, unit price and line total — the same item summed into
    one line, an addition included (003 RF-3). Unsent additions never
    count (003 RF-5): on a charged order they no longer exist."""
    from apps.orders.grouping import group_items
    from apps.orders.services import exclude_pending_send

    daily_number = f"N° {order.daily_number}" if order.daily_number is not None else "N°"
    stamp = timezone.localtime(moment).strftime("%d/%m/%Y %H:%M")
    lines = [
        _center(RECEIPT_TITLE, width),
        _center(subtitle, width),
        "-" * width,
        _pack_line(f"{daily_number}  {table_label(order)}", stamp, width),
        "-" * width,
    ]
    for group in group_items(exclude_pending_send(order.items.filter(is_voided=False))):
        lines.extend(_wrap(f"{group.quantity}x {to_ascii(group.name)}", width))
        lines.append(
            _pack_line(
                f"   {group.quantity} x {format_pesos(group.unit_price)}",
                format_pesos(group.line_total),
                width,
            )
        )
    return lines


def _totals(subtotal, discount, total, width) -> list[str]:
    lines = ["-" * width]
    if discount:
        lines.append(_pack_line("Subtotal", format_pesos(subtotal), width))
        lines.append(_pack_line("Descuento", f"-{format_pesos(discount)}", width))
    lines.append(_pack_line("TOTAL", format_pesos(total), width))
    return lines


def build_receipt_text(order, payment) -> str:
    width = _columns()
    lines = _header_and_items(order, RECEIPT_SUBTITLE, payment.charged_at, width)
    lines.extend(_totals(payment.subtotal, payment.discount, payment.amount, width))
    lines.extend(_wrap(f"Forma de pago: {to_ascii(payment.account.name)}", width))
    lines.append("-" * width)
    lines.append(_center(RECEIPT_FOOTER, width))
    return "\n".join(lines)


def build_bill_text(order, amounts) -> str:
    """RF-13: the order as it stands, with prices and the discount typed
    in the charge window — before paying, so no payment option, and a
    footer making clear it is not a receipt."""
    width = _columns()
    lines = _header_and_items(order, BILL_SUBTITLE, timezone.now(), width)
    lines.extend(
        _totals(amounts["subtotal"], amounts["discount"], amounts["total"], width)
    )
    lines.append("-" * width)
    lines.append(_center(BILL_FOOTER, width))
    return "\n".join(lines)
