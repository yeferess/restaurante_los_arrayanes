from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.menu import services
from apps.menu.models import Category, Product
from apps.menu.permissions import IsAdmin
from apps.menu.serializers import CategorySerializer, ProductSerializer


def _status_for(exc):
    return status.HTTP_409_CONFLICT if exc.code == "duplicate" else status.HTTP_400_BAD_REQUEST


def _parse_price(raw):
    """Accept the price as sent (number or string) but always hand the
    service a Decimal, or the original value if it can't be parsed at all
    so `_validate_price` rejects it uniformly."""
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return raw


class CategoryListCreateView(APIView):
    """GET/POST /api/menu/categorias (RF-1; GET also supports RF-2's selector)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        categories = Category.objects.order_by("name")
        return Response(CategorySerializer(categories, many=True).data)

    def post(self, request):
        try:
            category = services.create_category(request.data.get("name", ""))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(
            CategorySerializer(category).data, status=status.HTTP_201_CREATED
        )


class CategoryDetailView(APIView):
    """PATCH/DELETE /api/menu/categorias/{id} (RF-1)."""

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            category = services.rename_category(category, request.data.get("name", ""))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(CategorySerializer(category).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            services.delete_category(category)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductListCreateView(APIView):
    """GET/POST /api/menu/productos (RF-2..RF-5 management listing; RF-2
    creation). GET here includes unavailable products — it feeds the
    admin panel, not the mesero's menu (RF-7, see `MenuReadView`)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        products = Product.objects.select_related("category").order_by("name")
        return Response(ProductSerializer(products, many=True).data)

    def post(self, request):
        data = request.data
        try:
            product = services.create_product(
                name=data.get("name", ""),
                category_id=data.get("category_id"),
                price=_parse_price(data.get("price")),
                is_available=data.get("is_available"),
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(
            ProductSerializer(product).data, status=status.HTTP_201_CREATED
        )


class ProductDetailView(APIView):
    """PATCH/DELETE /api/menu/productos/{id} (RF-3, RF-5)."""

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        data = request.data
        try:
            product = services.update_product(
                product,
                name=data.get("name"),
                category_id=data.get("category_id"),
                price=_parse_price(data.get("price")) if "price" in data else None,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        services.delete_product(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductAvailabilityView(APIView):
    """POST /api/menu/productos/{id}/disponibilidad (RF-4)."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if "is_available" not in request.data:
            return Response(
                {"detail": "El campo 'is_available' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = services.set_product_availability(
            product, is_available=bool(request.data["is_available"])
        )
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)


class MenuReadView(APIView):
    """GET /api/menu (RF-7). Any authenticated account (admin or mesero);
    unlike `ProductListCreateView`'s admin-only listing, this never
    includes unavailable products (RF-4)."""

    def get(self, request):
        products = Product.objects.filter(is_available=True).select_related(
            "category"
        )
        return Response(ProductSerializer(products, many=True).data)
