"""Accounts app: custom user model and authentication."""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """LabVault user with role-based access control.

    Roles: student (default), administrator.
    Inherits email, password hashing (pbkdf2 via Django), first_name,
    last_name, is_active, date_joined from AbstractUser.
    """

    ROLE_STUDENT = "student"
    ROLE_ADMIN = "administrator"

    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_ADMIN, "Administrator"),
    ]

    email = models.EmailField(unique=True, blank=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    objects = UserManager()

    # Use email as the username field for authentication.
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        db_table = "Users"
        verbose_name = "user"
        verbose_name_plural = "users"

    @property
    def full_name(self):
        return self.get_full_name() or self.email

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_administrator(self):
        return self.role == self.ROLE_ADMIN

    def __str__(self):
        return self.email


class LoginAttempt(models.Model):
    """Per-email and per-client failed-login counter with a temporary lock."""

    email = models.EmailField(max_length=254)
    ip_address = models.GenericIPAddressField()
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    last_attempt_at = models.DateTimeField(auto_now=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "LoginAttempts"
        constraints = [
            models.UniqueConstraint(
                fields=["email", "ip_address"], name="unique_login_attempt_email_ip"
            )
        ]
        indexes = [
            models.Index(fields=["locked_until"], name="IX_LoginAttempts_LockedUntil"),
        ]

    def __str__(self):
        return f"Login failures for {self.email} from {self.ip_address}"
