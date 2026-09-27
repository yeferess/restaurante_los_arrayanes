from django.urls import path

from apps.accounts.views import (
    AdminLoginView,
    ChangeOwnPasswordView,
    CreateAdminView,
    CreateMeseroView,
    DeactivateMeseroView,
    HeartbeatView,
    LogoutView,
    MeseroLoginView,
    ReactivateMeseroView,
    ResetMeseroPinView,
    SessionInfoView,
    UnlockMeseroView,
)

urlpatterns = [
    path("auth/admin/login", AdminLoginView.as_view(), name="admin-login"),
    path("auth/mesero/login", MeseroLoginView.as_view(), name="mesero-login"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("auth/heartbeat", HeartbeatView.as_view(), name="heartbeat"),
    path("auth/session", SessionInfoView.as_view(), name="session"),
    path("usuarios/meseros", CreateMeseroView.as_view(), name="create-mesero"),
    path(
        "usuarios/meseros/<int:pk>/reset-pin",
        ResetMeseroPinView.as_view(),
        name="reset-mesero-pin",
    ),
    path(
        "usuarios/meseros/<int:pk>/desactivar",
        DeactivateMeseroView.as_view(),
        name="deactivate-mesero",
    ),
    path(
        "usuarios/meseros/<int:pk>/reactivar",
        ReactivateMeseroView.as_view(),
        name="reactivate-mesero",
    ),
    path(
        "usuarios/meseros/<int:pk>/desbloquear",
        UnlockMeseroView.as_view(),
        name="unlock-mesero",
    ),
    path("usuarios/admins", CreateAdminView.as_view(), name="create-admin"),
    path(
        "usuarios/admins/me/password",
        ChangeOwnPasswordView.as_view(),
        name="change-own-password",
    ),
]
