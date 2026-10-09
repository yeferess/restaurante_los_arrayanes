import threading
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase

from apps.kitchen_printing import services
from apps.kitchen_printing.adapters import PrinterFailureError, PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.models import PrintJob
from apps.orders.models import Order

User = get_user_model()


def _patched_adapter(adapter):
    return patch("apps.kitchen_printing.services.get_printer_adapter", return_value=adapter)


class PendingJobConsolidationTests(TestCase):
    """T15 — consolidation: at most one PENDING PrintJob per order (RF-8)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="w15", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=1, waiter=self.waiter)

    def test_creates_a_new_pending_job_when_there_is_none(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.ADDITION)
        jobs = list(PrintJob.objects.filter(order=self.order))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].ticket_type, PrintJob.TicketType.ADDITION)
        self.assertEqual(jobs[0].status, PrintJob.Status.PENDING)

    def test_reuses_the_existing_pending_job_instead_of_creating_another(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.ADDITION)
            services.register_event_and_print(self.order, PrintJob.TicketType.VOID)
        self.assertEqual(PrintJob.objects.filter(order=self.order).count(), 1)

    def test_keeps_the_original_ticket_type_fixed_once_created(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.ADDITION)
            services.register_event_and_print(self.order, PrintJob.TicketType.VOID)
        job = PrintJob.objects.get(order=self.order)
        self.assertEqual(job.ticket_type, PrintJob.TicketType.ADDITION)


class PrintAttemptTests(TestCase):
    """T16 — register_event_and_print: attempt & outcome (RF-9)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="w16", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=2, waiter=self.waiter)

    def test_successful_print_marks_the_job_printed(self):
        adapter = FakePrinterAdapter()
        with _patched_adapter(adapter):
            warning = services.register_event_and_print(
                self.order, PrintJob.TicketType.NEW_ORDER
            )
        self.assertIsNone(warning)
        job = PrintJob.objects.get(order=self.order)
        self.assertEqual(job.status, PrintJob.Status.PRINTED)
        self.assertIsNotNone(job.printed_at)
        self.assertEqual(adapter.call_count, 1)

    def test_printer_not_detected_leaves_the_job_pending_with_a_message(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            warning = services.register_event_and_print(
                self.order, PrintJob.TicketType.NEW_ORDER
            )
        self.assertIsNotNone(warning)
        job = PrintJob.objects.get(order=self.order)
        self.assertEqual(job.status, PrintJob.Status.PENDING)

    def test_printer_failure_leaves_the_job_pending_with_a_message(self):
        adapter = FakePrinterAdapter(fail_with=PrinterFailureError)
        with _patched_adapter(adapter):
            warning = services.register_event_and_print(
                self.order, PrintJob.TicketType.NEW_ORDER
            )
        self.assertIsNotNone(warning)
        job = PrintJob.objects.get(order=self.order)
        self.assertEqual(job.status, PrintJob.Status.PENDING)

    def test_attempts_increments_on_each_try_while_still_pending(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.NEW_ORDER)
            services.register_event_and_print(self.order, PrintJob.TicketType.ADDITION)
        job = PrintJob.objects.get(order=self.order)
        self.assertEqual(job.attempts, 2)


class PrintLockSerializationTests(TransactionTestCase):
    """T17 — a process-wide lock keeps two concurrent print attempts from
    ever reaching the adapter at the same time (single physical printer)."""

    def test_two_concurrent_print_attempts_never_overlap(self):
        waiter = User.objects.create_user(
            username="w17", password="1234", role=User.Role.MESERO
        )
        order_a = Order.objects.create(table_number=3, waiter=waiter)
        order_b = Order.objects.create(table_number=4, waiter=waiter)
        PrintJob.objects.create(order=order_a, ticket_type=PrintJob.TicketType.NEW_ORDER)
        PrintJob.objects.create(order=order_b, ticket_type=PrintJob.TicketType.NEW_ORDER)

        active = []
        overlap_detected = threading.Event()

        class SlowAdapter(FakePrinterAdapter):
            def print_ticket(self, text):
                active.append(1)
                if len(active) > 1:
                    overlap_detected.set()
                time.sleep(0.05)
                active.pop()
                return super().print_ticket(text)

        errors = []

        def _run(order, event_type):
            try:
                services.register_event_and_print(order, event_type)
            except Exception as exc:  # pragma: no cover - diagnostic aid
                errors.append(exc)
            finally:
                from django.db import connection

                connection.close()

        adapter = SlowAdapter()
        with _patched_adapter(adapter):
            t1 = threading.Thread(
                target=_run, args=(order_a, PrintJob.TicketType.NEW_ORDER)
            )
            t2 = threading.Thread(
                target=_run, args=(order_b, PrintJob.TicketType.NEW_ORDER)
            )
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        self.assertEqual(errors, [])
        self.assertFalse(overlap_detected.is_set())
        self.assertEqual(adapter.call_count, 2)


class RetryPrintTests(TestCase):
    """T18 — retry_print: owner-only, blocked after charge/void, retries
    the pending job (RF-9, RF-10, RF-11)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="w18", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="w18b", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=5, waiter=self.waiter)

    def test_rejects_a_waiter_who_does_not_own_the_order(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.NEW_ORDER)
            with self.assertRaises(ValidationError):
                services.retry_print(self.order, self.other_waiter)

    def test_rejects_when_the_order_is_already_charged(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.NEW_ORDER)
        self.order.status = Order.Status.CHARGED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.retry_print(self.order, self.waiter)

    def test_rejects_when_the_order_is_already_voided(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.NEW_ORDER)
        self.order.status = Order.Status.VOIDED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            services.retry_print(self.order, self.waiter)

    def test_rejects_when_there_is_no_pending_ticket(self):
        with self.assertRaises(ValidationError):
            services.retry_print(self.order, self.waiter)

    def test_retries_the_pending_job_and_succeeds(self):
        failing_adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with _patched_adapter(failing_adapter):
            services.register_event_and_print(self.order, PrintJob.TicketType.NEW_ORDER)

        succeeding_adapter = FakePrinterAdapter()
        with _patched_adapter(succeeding_adapter):
            warning = services.retry_print(self.order, self.waiter)

        self.assertIsNone(warning)
        job = PrintJob.objects.get(order=self.order)
        self.assertEqual(job.status, PrintJob.Status.PRINTED)
        self.assertEqual(job.attempts, 2)
