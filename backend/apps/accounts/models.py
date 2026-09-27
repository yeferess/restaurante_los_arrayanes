import re

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

username_validator = RegexValidator(
    regex=r"^[a-z0-9_]{3,20}$",
    message=(
        "Username must be 3-20 characters: lowercase letters, digits and "
        "underscores only."
    ),
)

PIN_REGEX = re.compile(r"^[0-9]{4,6}$")


def validate_pin(value):
    """Mesero PIN: 4-6 numeric digits (RF-2)."""
    if not PIN_REGEX.fullmatch(value):
        raise ValidationError("PIN must be 4-6 digits, numbers only.")


def validate_admin_password(value):
    """Admin password: 8+ chars combining letters and digits (RF-6, RF-10)."""
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
        raise ValidationError("Password must combine letters and digits.")


class UserManager(BaseUserManager):
    """Creates users with a hashed password (never plain text)."""

    use_in_migrations = True

    def create_user(self, username, password, role, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not role:
            raise ValueError("Role is required")
        if role == self.model.Role.MESERO:
            validate_pin(password)
        elif role == self.model.Role.ADMIN:
            validate_admin_password(password)
        user = self.model(
            username=self.normalize_username(username), role=role, **extra_fields
        )
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    @staticmethod
    def normalize_username(username):
        """Usernames are case-insensitive for every purpose (RF-2)."""
        return username.strip().lower()


class User(AbstractBaseUser):
    """A single account table shared by admin and mesero roles (RF-2)."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MESERO = "MESERO", "Mesero"

    username = models.CharField(
        max_length=20, unique=True, validators=[username_validator]
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    # Lockout bookkeeping (RF-7)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)

    # Single active session per mesero (RF-9)
    current_session_key = models.CharField(max_length=40, null=True, blank=True)

    # Audit trail: who created this account (RF-2, RF-6, RF-11). Never
    # PROTECT-deleted: accounts are only ever soft-deactivated (RF-5, RF-10).
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return self.username


class AccountAction(models.Model):
    """Audit trail for sensitive actions on accounts (RF-11, constitution rule 4)."""

    class ActionType(models.TextChoices):
        CREATED = "CREATED", "Created"
        PIN_RESET = "PIN_RESET", "PIN reset"
        ACTIVATED = "ACTIVATED", "Activated"
        DEACTIVATED = "DEACTIVATED", "Deactivated"
        UNLOCKED = "UNLOCKED", "Unlocked"
        OWN_PASSWORD_CHANGED = "OWN_PASSWORD_CHANGED", "Own password changed"
        ADMIN_CREATED = "ADMIN_CREATED", "Admin created"
        ADMIN_PERMANENTLY_DEACTIVATED = (
            "ADMIN_PERMANENTLY_DEACTIVATED",
            "Admin permanently deactivated",
        )
        ADMIN_RENAMED = "ADMIN_RENAMED", "Admin renamed"
        AUTO_LOCKED = "AUTO_LOCKED", "Auto-locked after failed attempts"

    account = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="account_actions"
    )
    action_type = models.CharField(max_length=40, choices=ActionType.choices)
    performed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="performed_actions",
    )
    via_cli = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} on {self.account.username} @ {self.timestamp}"


class FailedLoginAttempt(models.Model):
    """Log of failed login attempts against a real account (RF-7).

    Attempts against a non-existent username are never persisted here;
    RF-1's decreasing counter is simulated instead (see services.py).
    """

    account = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="failed_login_attempts_log"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Failed login for {self.account.username} @ {self.timestamp}"
