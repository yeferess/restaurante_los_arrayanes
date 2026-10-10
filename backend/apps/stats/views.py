import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stats import services
from apps.stats.permissions import IsAdmin


def _parse_date(raw, default=None):
    if raw is None:
        return default, None
    try:
        return datetime.date.fromisoformat(raw), None
    except ValueError:
        return None, Response(
            {"detail": "Fecha inválida, se espera el formato YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DaySummaryView(APIView):
    """GET /api/estadisticas/resumen (RF-1, RF-2, RF-3, RF-4). Admin-only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        date, error = _parse_date(request.query_params.get("date"), default=datetime.date.today())
        if error:
            return error
        return Response(services.day_summary(date))


class RangeSummaryView(APIView):
    """GET /api/estadisticas/rango (RF-5). Admin-only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        raw_from = request.query_params.get("from")
        raw_to = request.query_params.get("to")
        if not raw_from or not raw_to:
            return Response(
                {"detail": "from y to son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start, error = _parse_date(raw_from)
        if error:
            return error
        end, error = _parse_date(raw_to)
        if error:
            return error
        if start > end:
            return Response(
                {"detail": "from no puede ser posterior a to."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(services.range_summary(start, end))


class DayMovementView(APIView):
    """GET /api/estadisticas/movimiento (RF-6, RF-7). Admin-only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        date, error = _parse_date(request.query_params.get("date"), default=datetime.date.today())
        if error:
            return error
        return Response(services.day_movement(date))
