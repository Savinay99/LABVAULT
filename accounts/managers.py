"""Accounts app models - manager."""

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Custom manager for the User model using email as the username."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        # Email identity is case-insensitive throughout LabVault.
        email = email.strip().lower()
        extra_fields.setdefault("role", "student")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["role"] = "administrator"
        return self.create_user(email, password, **extra_fields)
