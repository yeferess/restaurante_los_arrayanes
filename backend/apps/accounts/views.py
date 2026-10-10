from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.middleware import LAST_ACTIVITY_SESSION_KEY, ADMIN_INACTIVITY_TIMEOUT
from apps.accounts.models import AccountAction, User, validate_admin_password, validate_pin
from apps.accounts.permissions import IsActingOnOwnAdminAccount, IsAdmin
from apps.accounts.serializers import (
    AdminLoginSerializer,
    ChangeOwnPasswordSerializer,
    CreateAdminSerializer,
    CreateMeseroSerializer,
    MeseroLoginSerializer,
    ResetMeseroPinSerializer,
)
from apps.accounts.services import (
    attempt_login,
    has_open_tables,
    invalidate_previous_session,
    register_action,
)


def _user_payload(user):
    return {"id": user.id, "username": user.username, "role": user.role}


class AdminLoginView(APIView):
    """POST /api/auth/admin/login (RF-1, RF-7, RF-8)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = attempt_login(
            username=serializer.validated_data["username"],
            credential=serializer.validated_data["password"],
            expected_role=User.Role.ADMIN,
        )

        if result.status == "locked":
            return Response(
                {"detail": result.message}, status=status.HTTP_423_LOCKED
            )
        if result.status == "deactivated":
            return Response({"detail": result.message}, status=status.HTTP_403_FORBIDDEN)
        if not result.success:
            return Response(
                {
                    "detail": result.message,
                    "intentos_restantes": result.remaining_attempts,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        django_login(
            request, result.user, backend="django.contrib.auth.backends.ModelBackend"
        )
        request.session[LAST_ACTIVITY_SESSION_KEY] = timezone.now().isoformat()
        return Response(_user_payload(result.user), status=status.HTTP_200_OK)


class MeseroLoginView(APIView):
    """POST /api/auth/mesero/login (RF-1, RF-7, RF-9)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MeseroLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = attempt_login(
            username=serializer.validated_data["username"],
            credential=serializer.validated_data["pin"],
            expected_role=User.Role.MESERO,
        )

        if result.status == "locked":
            return Response(
                {"detail": result.message}, status=status.HTTP_423_LOCKED
            )
        if result.status == "deactivated":
            return Response({"detail": result.message}, status=status.HTTP_403_FORBIDDEN)
        if not result.success:
            return Response(
                {
                    "detail": result.message,
                    "intentos_restantes": result.remaining_attempts,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        django_login(
            request, result.user, backend="django.contrib.auth.backends.ModelBackend"
        )
        request.session.save()
        invalidate_previous_session(result.user, request.session.session_key)
        return Response(_user_payload(result.user), status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/auth/logout (RF-9). Requires an authenticated session."""

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HeartbeatView(APIView):
    """POST /api/auth/heartbeat (RF-8). Admin-only activity ping."""

    permission_classes = [IsAdmin]

    def post(self, request):
        request.session[LAST_ACTIVITY_SESSION_KEY] = timezone.now().isoformat()
        request.session.save()
        return Response(
            {"expira_en_seg": int(ADMIN_INACTIVITY_TIMEOUT.total_seconds())},
            status=status.HTTP_200_OK,
        )


class SessionInfoView(APIView):
    """GET /api/auth/session (RF-1 support, used by the frontend middleware)."""

    def get(self, request):
        return Response(_user_payload(request.user), status=status.HTTP_200_OK)


def _mesero_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_by": user.created_by_id,
        "created_at": user.created_at.isoformat(),
    }


class CreateMeseroView(APIView):
    """GET/POST /api/usuarios/meseros (RF-2). Admin-only.

    GET lists every mesero (active and inactive) — the admin panel uses
    this to offer a dropdown instead of asking for a raw id."""

    permission_classes = [IsAdmin]

    def get(self, request):
        meseros = User.objects.filter(role=User.Role.MESERO).order_by("username")
        return Response([_mesero_payload(m) for m in meseros])

    def post(self, request):
        serializer = CreateMeseroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        pin = serializer.validated_data["pin"]

        normalized = User.objects.normalize_username(username)
        if User.objects.filter(username=normalized).exists():
            return Response(
                {"detail": "Ese nombre de usuario ya existe."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            mesero = User.objects.create_user(
                username=username,
                password=pin,
                role=User.Role.MESERO,
                created_by=request.user,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        register_action(
            account=mesero,
            action_type=AccountAction.ActionType.CREATED,
            performed_by=request.user,
        )
        return Response(_mesero_payload(mesero), status=status.HTTP_201_CREATED)


class ResetMeseroPinView(APIView):
    """POST /api/usuarios/meseros/{id}/reset-pin (RF-4). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            mesero = User.objects.get(pk=pk, role=User.Role.MESERO)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ResetMeseroPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nuevo_pin = serializer.validated_data["nuevo_pin"]

        try:
            validate_pin(nuevo_pin)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        mesero.set_password(nuevo_pin)
        mesero.save(update_fields=["password"])

        if mesero.current_session_key:
            SessionStore(session_key=mesero.current_session_key).delete()
            mesero.current_session_key = None
            mesero.save(update_fields=["current_session_key"])

        register_action(
            account=mesero,
            action_type=AccountAction.ActionType.PIN_RESET,
            performed_by=request.user,
        )
        return Response(status=status.HTTP_200_OK)


class DeactivateMeseroView(APIView):
    """POST /api/usuarios/meseros/{id}/desactivar (RF-5). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            mesero = User.objects.get(pk=pk, role=User.Role.MESERO)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if has_open_tables(mesero):
            return Response(
                {"detail": "El mesero tiene mesas o pedidos abiertos."},
                status=status.HTTP_409_CONFLICT,
            )

        mesero.is_active = False
        mesero.save(update_fields=["is_active"])
        register_action(
            account=mesero,
            action_type=AccountAction.ActionType.DEACTIVATED,
            performed_by=request.user,
        )
        return Response(status=status.HTTP_200_OK)


class ReactivateMeseroView(APIView):
    """POST /api/usuarios/meseros/{id}/reactivar (RF-5). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            mesero = User.objects.get(pk=pk, role=User.Role.MESERO)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if mesero.is_active:
            return Response(
                {"detail": "La cuenta ya está activa."},
                status=status.HTTP_409_CONFLICT,
            )

        mesero.is_active = True
        mesero.save(update_fields=["is_active"])
        register_action(
            account=mesero,
            action_type=AccountAction.ActionType.ACTIVATED,
            performed_by=request.user,
        )
        return Response(status=status.HTTP_200_OK)


class UnlockMeseroView(APIView):
    """POST /api/usuarios/meseros/{id}/desbloquear (RF-3, RF-7). Admin-only.

    Unlocking always requires setting a new PIN in the same action — RF-7
    forbids unlocking without it.
    """

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            mesero = User.objects.get(pk=pk, role=User.Role.MESERO)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not mesero.is_locked:
            return Response(
                {"detail": "Esta cuenta no está bloqueada."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ResetMeseroPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nuevo_pin = serializer.validated_data["nuevo_pin"]

        try:
            validate_pin(nuevo_pin)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        mesero.set_password(nuevo_pin)
        mesero.is_locked = False
        mesero.locked_at = None
        mesero.failed_login_attempts = 0
        mesero.save(
            update_fields=[
                "password",
                "is_locked",
                "locked_at",
                "failed_login_attempts",
            ]
        )
        register_action(
            account=mesero,
            action_type=AccountAction.ActionType.UNLOCKED,
            performed_by=request.user,
        )
        return Response(status=status.HTTP_200_OK)


def _admin_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_by": user.created_by_id,
        "created_at": user.created_at.isoformat(),
    }


class CreateAdminView(APIView):
    """POST /api/usuarios/admins (RF-6, RF-10). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        normalized = User.objects.normalize_username(username)
        if User.objects.filter(username=normalized).exists():
            return Response(
                {"detail": "Ese nombre de usuario ya existe."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            new_admin = User.objects.create_user(
                username=username,
                password=password,
                role=User.Role.ADMIN,
                created_by=request.user,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        register_action(
            account=new_admin,
            action_type=AccountAction.ActionType.ADMIN_CREATED,
            performed_by=request.user,
        )
        return Response(_admin_payload(new_admin), status=status.HTTP_201_CREATED)


class ChangeOwnPasswordView(APIView):
    """POST /api/usuarios/admins/me/password (RF-6). Admin-only, self only."""

    permission_classes = [IsAdmin, IsActingOnOwnAdminAccount]

    def post(self, request):
        self.check_object_permissions(request, request.user)
        serializer = ChangeOwnPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not request.user.check_password(data["password_actual"]):
            return Response(
                {"detail": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if data["password_nueva"] != data["password_nueva_confirmacion"]:
            return Response(
                {"detail": "Las contraseñas nuevas no coinciden."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_admin_password(data["password_nueva"])
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(data["password_nueva"])
        request.user.save(update_fields=["password"])
        register_action(
            account=request.user,
            action_type=AccountAction.ActionType.OWN_PASSWORD_CHANGED,
            performed_by=request.user,
        )
        return Response(status=status.HTTP_200_OK)
