from django.urls import path

from apps.menu.views import (
    CategoryDetailView,
    CategoryListCreateView,
    MenuReadView,
    ProductAvailabilityView,
    ProductDetailView,
    ProductListCreateView,
)

urlpatterns = [
    path("menu", MenuReadView.as_view(), name="menu-read"),
    path(
        "menu/categorias",
        CategoryListCreateView.as_view(),
        name="menu-categories",
    ),
    path(
        "menu/categorias/<int:pk>",
        CategoryDetailView.as_view(),
        name="menu-category-detail",
    ),
    path(
        "menu/productos",
        ProductListCreateView.as_view(),
        name="menu-products",
    ),
    path(
        "menu/productos/<int:pk>",
        ProductDetailView.as_view(),
        name="menu-product-detail",
    ),
    path(
        "menu/productos/<int:pk>/disponibilidad",
        ProductAvailabilityView.as_view(),
        name="menu-product-availability",
    ),
]
