"""Pure business logic for the accounts module (RF-1..RF-11).

Kept free of HTTP/request concerns so it can be unit tested directly
(see specs/001-autenticacion-usuarios/plan.md, section 1 and 4).
"""

import hashlib
from datetime import timedelta
from dataclasses import dataclass
from typing import Optional

from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import AccountAction, FailedLoginAttempt, User

GENERIC_INVALID_CREDENTIALS_MESSAGE = "Usuario o contraseña incorrectos."
MAX_FAILED_ATTEMPTS = 5
ADMIN_AUTO_UNLOCK_AFTER = timedelta(minutes=20)

MESERO_LOCKED_MESSAGE = (
    "Tu cuenta está bloqueada. Habla con un administrador para resolverlo."
)
ADMIN_LOCKED_MESSAGE = (
    "Tu cuenta está bloqueada. Espera 20 minutos o contacta al operador "
    "técnico del sistema."
)
MESERO_DEACTIVATED_MESSAGE = (
    "Tu cuenta está desactivada. Habla con un administrador para resolverlo."
)
ADMIN_DEACTIVATED_MESSAGE = (
    "Tu cuenta fue desactivada permanentemente. Contacta al operador "
    "técnico si necesitas una cuenta nueva."
)


def _locked_message(user):
    return ADMIN_LOCKED_MESSAGE if user.role == User.Role.ADMIN else MESERO_LOCKED_MESSAGE


def _simulated_remaining_attempts(normalized_username):
    """Deterministic, non-persisted stand-in for a real attempts counter.

    Lets a non-existent (or wrong-role) username show the exact same
    message shape as a real account, without ever writing a
    FailedLoginAttempt row for an account that doesn't exist (RF-1).
    """
    digest = hashlib.sha256(normalized_username.encode("utf-8")).hexdigest()
    return MAX_FAILED_ATTEMPTS - (int(digest, 16) % MAX_FAILED_ATTEMPTS)


def _deactivated_message(user):
    return (
        ADMIN_DEACTIVATED_MESSAGE
        if user.role == User.Role.ADMIN
        else MESERO_DEACTIVATED_MESSAGE
    )


def _maybe_auto_unlock_admin(user):
    """A locked admin account unlocks itself 20 min after the lockout (RF-7)."""
    if (
        user.role == User.Role.ADMIN
        and user.is_locked
        and user.locked_at is not None
        and timezone.now() - user.locked_at >= ADMIN_AUTO_UNLOCK_AFTER
    ):
        user.is_locked = False
        user.locked_at = None
        user.failed_login_attempts = 0
        user.save(update_fields=["is_locked", "locked_at", "failed_login_attempts"])


def register_action(account, action_type, performed_by=None, via_cli=False):
    """Write one traceability row for a sensitive account action (RF-11)."""
    return AccountAction.objects.create(
        account=account,
        action_type=action_type,
        performed_by=performed_by,
        via_cli=via_cli,
    )


@dataclass
class LoginResult:
    success: bool
    user: Optional[User] = None
    status: str = ""
    message: str = ""
    remaining_attempts: Optional[int] = None


def attempt_login(username, credential, expected_role):
    """Check credentials for one role's entry point (RF-1).

    No distinction is made between a non-existent username, a username
    that exists under the other role, or a wrong password/PIN: all three
    return the exact same generic message, so login never reveals whether
    an account exists.
    """
    normalized = User.objects.normalize_username(username)
    try:
        user = User.objects.get(username=normalized, role=expected_role)
    except User.DoesNotExist:
        remaining = _simulated_remaining_attempts(normalized)
        return LoginResult(
            success=False,
            status="invalid_credentials",
            message=(
                f"{GENERIC_INVALID_CREDENTIALS_MESSAGE} Te quedan {remaining} "
                "intentos antes del bloqueo."
            ),
            remaining_attempts=remaining,
        )

    _maybe_auto_unlock_admin(user)

    if user.is_locked:
        return LoginResult(
            success=False, user=user, status="locked", message=_locked_message(user)
        )

    if not user.is_active:
        return LoginResult(
            success=False,
            user=user,
            status="deactivated",
            message=_deactivated_message(user),
        )

    if not user.check_password(credential):
        FailedLoginAttempt.objects.create(account=user)
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.is_locked = True
            user.locked_at = timezone.now()
            user.save(
                update_fields=["failed_login_attempts", "is_locked", "locked_at"]
            )
            register_action(
                account=user,
                action_type=AccountAction.ActionType.AUTO_LOCKED,
                performed_by=None,
            )
            return LoginResult(
                success=False,
                user=user,
                status="locked",
                message=_locked_message(user),
            )
        user.save(update_fields=["failed_login_attempts"])
        remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
        return LoginResult(
            success=False,
            status="invalid_credentials",
            message=(
                f"{GENERIC_INVALID_CREDENTIALS_MESSAGE} Te quedan {remaining} "
                "intentos antes del bloqueo."
            ),
            remaining_attempts=remaining,
        )

    if user.failed_login_attempts:
        user.failed_login_attempts = 0
        user.save(update_fields=["failed_login_attempts"])
    return LoginResult(success=True, user=user, status="ok")


def invalidate_previous_session(user, new_session_key):
    """Keep at most one active session per mesero (RF-9).

    If the account already has a different session recorded, that old
    session is deleted from the session store immediately, so any request
    still carrying its cookie is rejected on its next use.
    """
    previous_key = user.current_session_key
    if previous_key and previous_key != new_session_key:
        SessionStore(session_key=previous_key).delete()
    if previous_key != new_session_key:
        user.current_session_key = new_session_key
        user.save(update_fields=["current_session_key"])


def ensure_active_admin_remains(excluding=None):
    """Refuse whatever would leave zero active admin accounts (RF-6).

    Call this *before* deactivating/locking-out an admin, passing that
    admin as `excluding` to check what the count would be afterwards.
    """
    active_admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    if excluding is not None:
        active_admins = active_admins.exclude(pk=excluding.pk)
    if not active_admins.exists():
        raise ValidationError(
            "El sistema debe tener siempre al menos una cuenta admin activa."
        )


def has_open_tables(mesero):
    """Whether a mesero has open tables/orders (RF-5).

    Hook for the future orders/tables module, out of scope for this spec
    (specs/001-autenticacion-usuarios/spec.md, "Fuera de alcance"). Always
    False until that module exists.
    """
    return False
