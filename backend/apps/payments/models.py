from django.conf import settings
from django.db import models

from apps.orders.models import Order


class PaymentAccount(models.Model):
    """One entry of the single payment-option list the admin picks from
    when charging an order — "Efectivo" (fixed, seeded by migration)
    plus whatever accounts the admin creates (RF-2). Never edited once
    created; only deletable while unused (see apps.payments.services).
    """

    name = models.CharField(max_length=100, unique=True)
    is_fixed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Payment(models.Model):
    """A charge record for an order (RF-3). Never edited nor deleted
    once created (constitution, regla 4) — correcting one means voiding
    it (status=VOIDED) and registering a new one (RF-6). At most one
    ACTIVE payment per order at a time, enforced by the DB itself
    (RF-7), which also rejects a concurrent double-charge (RF-1).
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        VOIDED = "VOIDED", "Voided"

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="payments"
    )
    account = models.ForeignKey(
        PaymentAccount, on_delete=models.PROTECT, related_name="payments"
    )
    # RF-10: `subtotal` is the items total at charge time, `discount` an
    # optional peso amount the admin took off, and `amount` what was
    # actually paid (subtotal - discount) — the value statistics add up.
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=6, choices=Status.choices, default=Status.ACTIVE
    )
    charged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_charged",
    )
    charged_at = models.DateTimeField(auto_now_add=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_voided",
        null=True,
        blank=True,
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_payment_per_order",
            )
        ]

    def save(self, *args, **kwargs):
        if self.subtotal is None:
            self.subtotal = self.amount + (self.discount or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.id} for order {self.order_id} ({self.status})"
