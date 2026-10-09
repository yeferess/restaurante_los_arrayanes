from decimal import Decimal

from rest_framework import serializers

from apps.kitchen_printing.models import PrintJob
from apps.orders.models import Order, OrderItem, Table
from apps.payments.models import Payment


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ["number", "status"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "name",
            "unit_price",
            "quantity",
            "note",
            "line_type",
            "is_voided",
            "void_reason",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    has_pending_print = serializers.SerializerMethodField()
    active_payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "table_number",
            "waiter_id",
            "status",
            "delivered",
            "items",
            "total",
            "has_pending_print",
            "active_payment",
        ]

    def get_total(self, obj):
        return sum(
            (item.unit_price * item.quantity for item in obj.items.all() if not item.is_voided),
            Decimal("0.00"),
        )

    def get_has_pending_print(self, obj):
        return obj.print_jobs.filter(status=PrintJob.Status.PENDING).exists()

    def get_active_payment(self, obj):
        payment = obj.payments.filter(status=Payment.Status.ACTIVE).first()
        if payment is None:
            return None
        return {
            "account_name": payment.account.name,
            "amount": str(payment.amount),
            "charged_by": payment.charged_by.username,
            "charged_at": payment.charged_at.isoformat(),
        }
