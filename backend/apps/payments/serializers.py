from rest_framework import serializers

from apps.payments.models import PaymentAccount


class PaymentAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAccount
        fields = ["id", "name", "is_fixed"]
