"""Real printer adapter: sends ESC/POS bytes as a RAW job to the
Windows print spooler, using whatever driver is already installed for
the Epson TM-U220 (plan.md, section 4, decision 4). Deliberately does
*not* talk to the USB device directly (discarded alternative — see the
same section): that would require replacing the manufacturer's driver
with a generic libusb one, which risks breaking any other use the
restaurant makes of the same printer from Windows.
"""

import win32print
from django.conf import settings

from apps.kitchen_printing.adapters import (
    PrinterAdapter,
    PrinterFailureError,
    PrinterNotDetectedError,
)


class EscposUsbPrinterAdapter(PrinterAdapter):
    def __init__(self, printer_name: str | None = None):
        self.printer_name = printer_name or win32print.GetDefaultPrinter()

    def print_ticket(self, text: str, doc_name: str = "Ticket de cocina") -> None:
        try:
            handle = win32print.OpenPrinter(self.printer_name)
        except Exception as exc:
            raise PrinterNotDetectedError(str(exc)) from exc

        try:
            win32print.StartDocPrinter(handle, 1, (doc_name, None, "RAW"))
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, self._with_paper_feed(text))
            win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
        except Exception as exc:
            raise PrinterFailureError(str(exc)) from exc
        finally:
            win32print.ClosePrinter(handle)

    @staticmethod
    def _with_paper_feed(text: str) -> bytes:
        """Ends the last line and feeds blank lines so the whole ticket
        clears the tear bar — the TM-U220's print head sits a few lines
        below it. Plain line feeds, no extra ESC/POS commands."""
        feed_lines = getattr(settings, "KITCHEN_PRINTER_FEED_LINES", 6)
        return (text + "\n" * (1 + feed_lines)).encode("cp437", errors="replace")
