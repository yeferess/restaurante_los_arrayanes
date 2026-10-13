"""Plain-text customer receipt of a charged order (005-cobro RF-11).

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


def build_receipt_text(order, payment) -> str:
    width = _columns()
    daily_number = f"N° {order.daily_number}" if order.daily_number is not None else "N°"
    charged_at = timezone.localtime(payment.charged_at).strftime("%d/%m/%Y %H:%M")

    lines = [
        _center(RECEIPT_TITLE, width),
        _center(RECEIPT_SUBTITLE, width),
        "-" * width,
        _pack_line(f"{daily_number}  {table_label(order)}", charged_at, width),
        "-" * width,
    ]
    for item in order.items.filter(is_voided=False).order_by("id"):
        lines.extend(_wrap(f"{item.quantity}x {to_ascii(item.name)}", width))
        lines.append(
            _pack_line(
                f"   {item.quantity} x {format_pesos(item.unit_price)}",
                format_pesos(item.unit_price * item.quantity),
                width,
            )
        )
    lines.append("-" * width)
    if payment.discount:
        lines.append(_pack_line("Subtotal", format_pesos(payment.subtotal), width))
        lines.append(_pack_line("Descuento", f"-{format_pesos(payment.discount)}", width))
    lines.append(_pack_line("TOTAL", format_pesos(payment.amount), width))
    lines.extend(_wrap(f"Forma de pago: {to_ascii(payment.account.name)}", width))
    lines.append("-" * width)
    lines.append(_center(RECEIPT_FOOTER, width))
    return "\n".join(lines)
