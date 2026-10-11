from django.urls import path

from apps.kitchen_printing.views import ReprintOrderView, RetryPrintView

urlpatterns = [
    path(
        "pedidos/<int:pk>/reimprimir",
        RetryPrintView.as_view(),
        name="kitchen-printing-retry",
    ),
    path(
        "pedidos/<int:pk>/reimpresion",
        ReprintOrderView.as_view(),
        name="kitchen-printing-reprint",
    ),
]
