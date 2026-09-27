from datetime import timedelta

from django.contrib.auth import logout as django_logout
from django.http import JsonResponse
from django.utils import timezone

from apps.accounts.models import User

LAST_ACTIVITY_SESSION_KEY = "ultima_actividad"
ADMIN_INACTIVITY_TIMEOUT = timedelta(minutes=30)


class AdminInactivityMiddleware:
    """Closes an admin's session after 30 min without activity (RF-8).

    Must run after AuthenticationMiddleware, so `request.user` is already
    resolved from the session. Meseros (RF-9) are never touched here.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == User.Role.ADMIN
        ):
            last_activity_raw = request.session.get(LAST_ACTIVITY_SESSION_KEY)
            if last_activity_raw is not None:
                last_activity = timezone.datetime.fromisoformat(last_activity_raw)
                if timezone.now() - last_activity > ADMIN_INACTIVITY_TIMEOUT:
                    django_logout(request)
                    return JsonResponse(
                        {"detail": "Sesión expirada por inactividad."}, status=401
                    )

        return self.get_response(request)
