from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.kitchen_printing.models import PrintJob
from apps.orders.models import Order

User = get_user_model()


class PrintJobModelTests(TestCase):
    """T03 — `PrintJob` model (RF-8, RF-9, RF-10)."""

    def setUp(self):
        self.waiter = User.objects.create_user(
            username="mesero_pj", password="1234", role=User.Role.MESERO
        )
        self.order = Order.objects.create(table_number=1, waiter=self.waiter)

    def test_creating_a_print_job_defaults_to_pending_with_one_attempt(self):
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        self.assertEqual(job.status, PrintJob.Status.PENDING)
        self.assertEqual(job.attempts, 1)
        self.assertIsNone(job.printed_at)
        self.assertIsNotNone(job.created_at)

    def test_ticket_type_choices(self):
        for value in (
            PrintJob.TicketType.NEW_ORDER,
            PrintJob.TicketType.ADDITION,
            PrintJob.TicketType.VOID,
        ):
            job = PrintJob.objects.create(order=self.order, ticket_type=value)
            job.refresh_from_db()
            self.assertEqual(job.ticket_type, value)

    def test_status_can_be_set_to_printed(self):
        job = PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        from django.utils import timezone

        job.status = PrintJob.Status.PRINTED
        job.printed_at = timezone.now()
        job.save(update_fields=["status", "printed_at"])
        job.refresh_from_db()
        self.assertEqual(job.status, PrintJob.Status.PRINTED)
        self.assertIsNotNone(job.printed_at)

    def test_order_is_protected_from_deletion_while_a_print_job_exists(self):
        from django.db.models import ProtectedError

        PrintJob.objects.create(
            order=self.order, ticket_type=PrintJob.TicketType.NEW_ORDER
        )
        with self.assertRaises(ProtectedError):
            self.order.delete()
