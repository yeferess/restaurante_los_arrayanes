"""Printer adapter interface (plan.md, sections 1 and 4).

Keeps every caller (apps.kitchen_printing.services) ignorant of how the
ticket actually reaches paper, so a FakePrinterAdapter can stand in for
the real Epson TM-U220 in every automated test (see test_adapters_fake.py
and the T36 manual checklist, which is the only place the real hardware
is exercised).
"""

from abc import ABC, abstractmethod


class PrinterError(Exception):
    """Base class for the two failure categories RF-9 distinguishes."""


class PrinterNotDetectedError(PrinterError):
    """Could not even establish communication with the printer."""


class PrinterFailureError(PrinterError):
    """Communicated with the printer, but the print itself failed for
    any other reason (no paper, no ribbon, jam, a partial print, ...)."""


class PrinterAdapter(ABC):
    @abstractmethod
    def print_ticket(self, text: str, doc_name: str = "Ticket de cocina") -> None:
        """Print `text` as-is; `doc_name` is only the job's label in the
        Windows queue. Raises PrinterNotDetectedError or
        PrinterFailureError on failure; returns normally on success."""
