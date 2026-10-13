from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.kitchen_printing import services
from apps.kitchen_printing.permissions import IsMesero
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer


def _status_for(exc):
    if exc.code == "not_owner":
        return status.HTTP_403_FORBIDDEN
    if exc.code == "not_found":
        return status.HTTP_404_NOT_FOUND
    return status.HTTP_409_CONFLICT


class PrintOrderView(APIView):
    """POST /api/pedidos/{id}/imprimir (RF-1, RF-9, RF-10, RF-11):
    "Imprimir pedido". Owner-only. Also served at the old
    /reimprimir path (the former "Reintentar")."""

    permission_classes = [IsMesero]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            print_warning = services.print_order(order, request.user)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))

        data = OrderSerializer(order).data
        data["print_warning"] = print_warning
        return Response(data)


class ReprintOrderView(APIView):
    """POST /api/pedidos/{id}/reimpresion (RF-12). The order's own waiter
    while it is open, or any admin while it is open or charged — the
    role/status rules live in services.reprint_order."""

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            print_warning = services.reprint_order(order, request.user)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))

        data = OrderSerializer(order).data
        data["print_warning"] = print_warning
        return Response(data)
