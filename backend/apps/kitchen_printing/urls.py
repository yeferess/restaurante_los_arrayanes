from django.urls import path

from apps.kitchen_printing.views import PrintOrderView, ReprintOrderView

urlpatterns = [
    path(
        "pedidos/<int:pk>/imprimir",
        PrintOrderView.as_view(),
        name="kitchen-printing-print",
    ),
    # The former "Reintentar" — same action as "Imprimir pedido" now.
    path(
        "pedidos/<int:pk>/reimprimir",
        PrintOrderView.as_view(),
        name="kitchen-printing-retry",
    ),
    path(
        "pedidos/<int:pk>/reimpresion",
        ReprintOrderView.as_view(),
        name="kitchen-printing-reprint",
    ),
]
