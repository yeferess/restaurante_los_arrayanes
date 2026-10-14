from django.urls import path

from apps.payments.views import (
    AccountDeleteView,
    AccountListCreateView,
    BillView,
    PreviewChargeView,
    ReceiptView,
    VoidChargeView,
)

urlpatterns = [
    path(
        "pedidos/<int:pk>/cobro/anular",
        VoidChargeView.as_view(),
        name="payments-void-charge",
    ),
    path(
        "pedidos/<int:pk>/cobro/previsualizar",
        PreviewChargeView.as_view(),
        name="payments-preview-charge",
    ),
    path(
        "pedidos/<int:pk>/comprobante",
        ReceiptView.as_view(),
        name="payments-receipt",
    ),
    path("pedidos/<int:pk>/cuenta", BillView.as_view(), name="payments-bill"),
    path(
        "cuentas-pago", AccountListCreateView.as_view(), name="payments-accounts"
    ),
    path(
        "cuentas-pago/<int:pk>",
        AccountDeleteView.as_view(),
        name="payments-account-delete",
    ),
]
