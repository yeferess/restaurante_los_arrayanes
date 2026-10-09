from django.conf import settings

from apps.kitchen_printing.adapters import PrinterAdapter
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter


def get_printer_adapter() -> PrinterAdapter:
    """Returns the printer adapter selected by settings.py — "fake" in
    tests, "escpos" (the real Epson TM-U220) otherwise."""
    adapter_name = getattr(settings, "KITCHEN_PRINTER_ADAPTER", "escpos")
    if adapter_name == "fake":
        return FakePrinterAdapter()

    from apps.kitchen_printing.escpos_adapter import EscposUsbPrinterAdapter

    return EscposUsbPrinterAdapter()
