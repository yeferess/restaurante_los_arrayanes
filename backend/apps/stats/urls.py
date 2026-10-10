from django.urls import path

from apps.stats.views import DayMovementView, DaySummaryView, RangeSummaryView

urlpatterns = [
    path("estadisticas/resumen", DaySummaryView.as_view(), name="stats-day-summary"),
    path("estadisticas/rango", RangeSummaryView.as_view(), name="stats-range-summary"),
    path(
        "estadisticas/movimiento",
        DayMovementView.as_view(),
        name="stats-day-movement",
    ),
]
