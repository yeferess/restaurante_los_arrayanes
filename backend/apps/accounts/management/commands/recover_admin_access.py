from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import AccountAction, User, validate_admin_password
from apps.accounts.services import register_action


class Command(BaseCommand):
    """Recovers an admin's access: unlocks the account, resets the
    password, or both in the same run (RF-7, RF-10).

    Always unlocks immediately, without waiting for the 20-minute
    auto-unlock. The password is only changed when --password is given.
    """

    help = "Unlocks an admin account and/or resets its password (server-only)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument(
            "--password", required=False, help="New password. Omit to only unlock."
        )

    def handle(self, *args, **options):
        username = options["username"]
        new_password = options.get("password")

        try:
            admin = User.objects.get(
                username=User.objects.normalize_username(username),
                role=User.Role.ADMIN,
            )
        except User.DoesNotExist:
            raise CommandError(f"No admin account found for '{username}'.")

        if new_password:
            try:
                validate_admin_password(new_password)
            except DjangoValidationError as exc:
                raise CommandError("; ".join(exc.messages))

        admin.is_locked = False
        admin.locked_at = None
        admin.failed_login_attempts = 0
        update_fields = ["is_locked", "locked_at", "failed_login_attempts"]

        if new_password:
            admin.set_password(new_password)
            update_fields.append("password")

        admin.save(update_fields=update_fields)

        register_action(
            account=admin,
            action_type=AccountAction.ActionType.UNLOCKED,
            performed_by=None,
            via_cli=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Access recovered for admin '{admin.username}'.")
        )
