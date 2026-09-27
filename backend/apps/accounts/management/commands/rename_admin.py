from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import AccountAction, User
from apps.accounts.services import register_action


class Command(BaseCommand):
    """Renames an admin account's username (RF-10).

    The only way to change an admin's username — RF-6 forbids it from the
    web panel, even for one's own account. Honors the same format and
    global uniqueness rules as the panel (RF-2).
    """

    help = "Renames an admin account's username (server-only, RF-10)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Current username.")
        parser.add_argument("--new-username", required=True, dest="new_username")

    def handle(self, *args, **options):
        username = options["username"]
        new_username = options["new_username"]

        try:
            admin = User.objects.get(
                username=User.objects.normalize_username(username),
                role=User.Role.ADMIN,
            )
        except User.DoesNotExist:
            raise CommandError(f"No admin account found for '{username}'.")

        normalized_new = User.objects.normalize_username(new_username)
        if User.objects.filter(username=normalized_new).exists():
            raise CommandError(f"Username '{new_username}' is already taken.")

        admin.username = normalized_new
        try:
            admin.full_clean()
        except DjangoValidationError as exc:
            raise CommandError("; ".join(exc.messages))

        update_fields = ["username"]
        if admin.current_session_key:
            SessionStore(session_key=admin.current_session_key).delete()
            admin.current_session_key = None
            update_fields.append("current_session_key")

        admin.save(update_fields=update_fields)

        register_action(
            account=admin,
            action_type=AccountAction.ActionType.ADMIN_RENAMED,
            performed_by=None,
            via_cli=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Admin renamed to '{admin.username}'."))
