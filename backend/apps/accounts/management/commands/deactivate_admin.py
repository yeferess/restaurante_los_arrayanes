from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import AccountAction, User
from apps.accounts.services import ensure_active_admin_remains, register_action


class Command(BaseCommand):
    """Permanently deactivates an admin account (RF-10).

    Never deletes the row, so every AccountAction referencing it (as the
    account acted on, or as the performer of a past action) stays intact
    (RF-11). There is no command to reverse this — a new admin must be
    created instead. Refuses to leave the system with zero active admins
    (RF-6).
    """

    help = "Permanently deactivates an admin account (server-only, RF-10)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        username = options["username"]

        try:
            admin = User.objects.get(
                username=User.objects.normalize_username(username),
                role=User.Role.ADMIN,
            )
        except User.DoesNotExist:
            raise CommandError(f"No admin account found for '{username}'.")

        try:
            ensure_active_admin_remains(excluding=admin)
        except DjangoValidationError as exc:
            raise CommandError("; ".join(exc.messages))

        admin.is_active = False
        update_fields = ["is_active"]

        if admin.current_session_key:
            SessionStore(session_key=admin.current_session_key).delete()
            admin.current_session_key = None
            update_fields.append("current_session_key")

        admin.save(update_fields=update_fields)

        register_action(
            account=admin,
            action_type=AccountAction.ActionType.ADMIN_PERMANENTLY_DEACTIVATED,
            performed_by=None,
            via_cli=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Admin '{admin.username}' permanently deactivated.")
        )
