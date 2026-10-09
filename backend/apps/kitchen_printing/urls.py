from django.urls import path

from apps.kitchen_printing.views import RetryPrintView

urlpatterns = [
    path(
        "pedidos/<int:pk>/reimprimir",
        RetryPrintView.as_view(),
        name="kitchen-printing-retry",
    ),
]
