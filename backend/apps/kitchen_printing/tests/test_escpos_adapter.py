from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.kitchen_printing.adapters import PrinterFailureError, PrinterNotDetectedError
from apps.kitchen_printing.escpos_adapter import EscposUsbPrinterAdapter


class EscposUsbPrinterAdapterTests(TestCase):
    """T07 — EscposUsbPrinterAdapter: sends raw ESC/POS bytes to the
    Windows print spooler using the Epson driver already installed
    (plan.md, section 4). Mocks win32print entirely — there is no way
    to exercise the real hardware from an automated test (see the
    manual checklist, T36)."""

    @patch("apps.kitchen_printing.escpos_adapter.win32print")
    def test_success_path_opens_writes_and_closes_in_order(self, mock_win32print):
        mock_win32print.OpenPrinter.return_value = "handle-1"
        adapter = EscposUsbPrinterAdapter(printer_name="Epson TM-U220")

        adapter.print_ticket("hola cocina")

        mock_win32print.OpenPrinter.assert_called_once_with("Epson TM-U220")
        mock_win32print.StartDocPrinter.assert_called_once()
        mock_win32print.StartPagePrinter.assert_called_once_with("handle-1")
        mock_win32print.WritePrinter.assert_called_once()
        written_bytes = mock_win32print.WritePrinter.call_args[0][1]
        self.assertEqual(written_bytes, "hola cocina".encode("cp437", errors="replace"))
        mock_win32print.EndPagePrinter.assert_called_once_with("handle-1")
        mock_win32print.EndDocPrinter.assert_called_once_with("handle-1")
        mock_win32print.ClosePrinter.assert_called_once_with("handle-1")

    @patch("apps.kitchen_printing.escpos_adapter.win32print")
    def test_printer_not_found_raises_printer_not_detected_error(self, mock_win32print):
        mock_win32print.OpenPrinter.side_effect = Exception("printer offline")
        adapter = EscposUsbPrinterAdapter(printer_name="Epson TM-U220")

        with self.assertRaises(PrinterNotDetectedError):
            adapter.print_ticket("hola")

    @patch("apps.kitchen_printing.escpos_adapter.win32print")
    def test_a_failure_after_opening_raises_printer_failure_error(self, mock_win32print):
        mock_win32print.OpenPrinter.return_value = "handle-1"
        mock_win32print.WritePrinter.side_effect = Exception("sin papel")
        adapter = EscposUsbPrinterAdapter(printer_name="Epson TM-U220")

        with self.assertRaises(PrinterFailureError):
            adapter.print_ticket("hola")

        mock_win32print.ClosePrinter.assert_called_once_with("handle-1")

    @patch("apps.kitchen_printing.escpos_adapter.win32print")
    def test_uses_the_default_printer_when_no_name_is_given(self, mock_win32print):
        mock_win32print.GetDefaultPrinter.return_value = "Default Printer"
        mock_win32print.OpenPrinter.return_value = "handle-1"

        adapter = EscposUsbPrinterAdapter()
        adapter.print_ticket("hola")

        mock_win32print.OpenPrinter.assert_called_once_with("Default Printer")
