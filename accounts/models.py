"""Accounts app: custom user model and authentication."""

from django.contrib.auth.models import AbstractUser
from django.db import models


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
