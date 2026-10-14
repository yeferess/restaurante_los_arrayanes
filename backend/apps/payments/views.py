from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.serializers import AdminOrderSerializer
from apps.payments import services
from apps.payments.models import PaymentAccount
from apps.payments.permissions import IsAdmin
from apps.payments.serializers import PaymentAccountSerializer


def _status_for(exc):
    if exc.code == "invalid":
        return status.HTTP_400_BAD_REQUEST
    if exc.code == "not_found":
        return status.HTTP_404_NOT_FOUND
    return status.HTTP_409_CONFLICT


class VoidChargeView(APIView):
    """POST /api/pedidos/{id}/cobro/anular (RF-6, RF-8). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason")
        try:
            services.void_charge(order, request.user, reason)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))

        return Response(AdminOrderSerializer(order).data)


def _get_order_or_404(pk):
    try:
        return Order.objects.get(pk=pk), None
    except Order.DoesNotExist:
        return None, Response(status=status.HTTP_404_NOT_FOUND)


class PreviewChargeView(APIView):
    """POST /api/pedidos/{id}/cobro/previsualizar (RF-10). Admin-only:
    subtotal, discount and total to pay — saves nothing."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        order, error = _get_order_or_404(pk)
        if error:
            return error
        try:
            amounts = services.preview_charge(order, request.data.get("discount"))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response({key: str(value) for key, value in amounts.items()})


class ReceiptView(APIView):
    """POST /api/pedidos/{id}/comprobante (RF-11). Admin-only: prints the
    customer receipt of a charged order."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        order, error = _get_order_or_404(pk)
        if error:
            return error
        try:
            warning = services.print_receipt(order)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response({"print_warning": warning})


class BillView(APIView):
    """POST /api/pedidos/{id}/cuenta (RF-13). Admin-only: prints the bill
    of an order still to be paid, with the optional discount typed in
    the charge window. Charges nothing."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        order, error = _get_order_or_404(pk)
        if error:
            return error
        try:
            warning = services.print_bill(order, request.data.get("discount"))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response({"print_warning": warning})


class AccountListCreateView(APIView):
    """GET/POST /api/cuentas-pago (RF-2, RF-8). Admin-only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        accounts = PaymentAccount.objects.order_by("name")
        return Response(PaymentAccountSerializer(accounts, many=True).data)

    def post(self, request):
        try:
            account = services.create_account(request.data.get("name"))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(
            PaymentAccountSerializer(account).data, status=status.HTTP_201_CREATED
        )


class AccountDeleteView(APIView):
    """DELETE /api/cuentas-pago/{id} (RF-2, RF-8). Admin-only."""

    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        try:
            account = PaymentAccount.objects.get(pk=pk)
        except PaymentAccount.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            services.delete_account(account)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(status=status.HTTP_204_NO_CONTENT)
