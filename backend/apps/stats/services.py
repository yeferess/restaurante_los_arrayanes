"""Read-only aggregations over Order/OrderItem/Payment (RF-1 a RF-10).

Never writes anything — see spec.md RF-9. Two distinct date criteria
coexist here and must never be mixed: money is grouped by `charged_at`
(005), orders/products by `sent_at` (003-RF-14).
"""

from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate

from apps.orders.models import Order, OrderItem
from apps.orders.services import exclude_pending_send
from apps.payments.models import Payment


def _order_total(order):
    """Same calculation as apps.orders.serializers.OrderSerializer.get_total
    — the order's *current* total, never a historical snapshot (RF-6);
    an addition the waiter hasn't sent yet doesn't count (003 RF-5)."""
    return sum(
        (
            item.unit_price * item.quantity
            for item in exclude_pending_send(order.items.filter(is_voided=False))
        ),
        Decimal("0.00"),
    )


def _qualifying_payments(start, end):
    """RF-10: a payment counts toward its own charge day if it is still
    ACTIVE, or if it was voided on a date *later* than its own
    charged_at — comparing a payment against its own dates (never
    against "today") is what makes an already-closed day's totals
    permanently stable."""
    return (
        Payment.objects.annotate(
            charged_date=TruncDate("charged_at"),
            voided_date=TruncDate("voided_at"),
        )
        .filter(charged_date__range=(start, end))
        .filter(Q(status=Payment.Status.ACTIVE) | Q(voided_date__gt=F("charged_date")))
    )


def money_total(start, end):
    total = _qualifying_payments(start, end).aggregate(total=Sum("amount"))["total"]
    return total or 0


def orders_charged_count(start, end):
    return _qualifying_payments(start, end).values("order_id").distinct().count()


def money_by_account(start, end):
    return list(
        _qualifying_payments(start, end)
        .values(account_name=F("account__name"))
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )


def orders_sent_count(start, end):
    return Order.objects.filter(sent_at__date__range=(start, end)).count()


def orders_by_waiter(start, end):
    return list(
        Order.objects.filter(sent_at__date__range=(start, end))
        .values(waiter_username=F("waiter__username"))
        .annotate(orders_sent=Count("id"))
        .order_by("-orders_sent")
    )


def range_summary(start, end):
    """RF-5 (also the base of day_summary, RF-1): every metric for an
    arbitrary date range — a future `end` simply yields no data for the
    days that haven't happened yet."""
    return {
        "from": start,
        "to": end,
        "money_total": money_total(start, end),
        "orders_sent_count": orders_sent_count(start, end),
        "money_by_account": money_by_account(start, end),
        "orders_by_waiter": orders_by_waiter(start, end),
        "top_products": top_products(start, end),
    }


def day_summary(date):
    """RF-1: the special case of range_summary() for a single day, with
    the one extra metric that only makes sense for a single day
    (orders_charged_count, RF-1) instead of orders_sent_count."""
    summary = range_summary(date, date)
    summary = {k: v for k, v in summary.items() if k not in ("from", "to", "orders_sent_count")}
    summary["date"] = date
    summary["orders_charged_count"] = orders_charged_count(date, date)
    return summary


def top_products(start, end):
    return list(
        exclude_pending_send(
            OrderItem.objects.filter(
                order__sent_at__date__range=(start, end),
                is_voided=False,
                catalog_product__isnull=False,
            )
        )
        .exclude(order__status=Order.Status.VOIDED)
        .values(product_name=F("catalog_product__name"))
        .annotate(quantity=Sum("quantity"))
        .order_by("-quantity")[:10]
    )


def day_movement(date):
    """RF-6: the raw list of orders sent and payments registered on a
    single day, including voided ones (for traceability) — never
    filtered the way the aggregations above are."""
    orders = Order.objects.filter(sent_at__date=date).select_related("waiter")
    payments = (
        Payment.objects.annotate(charged_date=TruncDate("charged_at"))
        .filter(charged_date=date)
        .select_related("account", "charged_by")
    )
    return {
        "date": date,
        "orders": [
            {
                "daily_number": order.daily_number,
                "waiter": order.waiter.username,
                "status": order.status,
                "total": _order_total(order),
            }
            for order in orders
        ],
        "payments": [
            {
                "account_name": payment.account.name,
                "amount": payment.amount,
                "charged_by": payment.charged_by.username,
                "charged_at": payment.charged_at,
                "status": payment.status,
            }
            for payment in payments
        ],
    }
