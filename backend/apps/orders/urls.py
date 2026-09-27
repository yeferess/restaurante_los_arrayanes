from django.urls import path

from apps.orders.views import (
    AddItemView,
    ChargeOrderView,
    CreateOrderView,
    FixTableView,
    IncomingOrdersView,
    MyOrdersView,
    OrderDetailView,
    ReleaseTableView,
    RemoveItemView,
    ResizeTablesView,
    SendOrderView,
    SetDeliveredView,
    TableListView,
    UpdateItemNoteView,
    VoidItemView,
    VoidOrderView,
)

urlpatterns = [
    path("mesas", TableListView.as_view(), name="orders-tables"),
    path("mesas/numero", ResizeTablesView.as_view(), name="orders-resize-tables"),
    path(
        "mesas/<int:numero>/liberar",
        ReleaseTableView.as_view(),
        name="orders-release-table",
    ),
    path("pedidos", CreateOrderView.as_view(), name="orders-create"),
    path("pedidos/mios", MyOrdersView.as_view(), name="orders-mine"),
    path("pedidos/entrantes", IncomingOrdersView.as_view(), name="orders-incoming"),
    path("pedidos/<int:pk>", OrderDetailView.as_view(), name="orders-detail"),
    path("pedidos/<int:pk>/items", AddItemView.as_view(), name="orders-add-item"),
    path(
        "pedidos/<int:pk>/items/<int:item_id>",
        RemoveItemView.as_view(),
        name="orders-remove-item",
    ),
    path(
        "pedidos/<int:pk>/items/<int:item_id>/anular",
        VoidItemView.as_view(),
        name="orders-void-item",
    ),
    path(
        "pedidos/<int:pk>/items/<int:item_id>/nota",
        UpdateItemNoteView.as_view(),
        name="orders-item-note",
    ),
    path("pedidos/<int:pk>/enviar", SendOrderView.as_view(), name="orders-send"),
    path("pedidos/<int:pk>/mesa", FixTableView.as_view(), name="orders-fix-table"),
    path(
        "pedidos/<int:pk>/entregado",
        SetDeliveredView.as_view(),
        name="orders-delivered",
    ),
    path("pedidos/<int:pk>/cobrar", ChargeOrderView.as_view(), name="orders-charge"),
    path("pedidos/<int:pk>/anular", VoidOrderView.as_view(), name="orders-void"),
]
