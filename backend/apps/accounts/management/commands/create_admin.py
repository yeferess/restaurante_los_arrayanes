from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import AccountAction, User
from apps.accounts.services import register_action


class Command(BaseCommand):
    """Creates an admin account (RF-10).

    The very first admin must be created this way, before anyone can use
    /admin. Running it again with a different username just creates an
    additional admin — the system supports several admins simultaneously.
    """

    help = "Creates an admin account (server-only, RF-10)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        try:
            admin = User.objects.create_user(
                username=username, password=password, role=User.Role.ADMIN
            )
        except DjangoValidationError as exc:
            raise CommandError("; ".join(exc.messages))

        register_action(
            account=admin,
            action_type=AccountAction.ActionType.ADMIN_CREATED,
            performed_by=None,
            via_cli=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Admin '{admin.username}' created."))
