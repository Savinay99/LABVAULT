"""Social auth pipeline helpers for LabVault.

create_user_by_email: On first social login, create a LabVault user account
matched by the provider's verified email address. If an account already
exists with that email, link the social account to it instead of creating
a duplicate.
"""

from django.contrib.auth import get_user_model

User = get_user_model()


def create_user_by_email(strategy, details, user=None, *args, **kwargs):
    """Create/link a user by verified email during social auth pipeline."""
    if user:
        # Social account already associated with an existing user.
        return {"user": user, "is_new": False}

    email = (details.get("email") or "").strip().lower()
    if not email:
        return None  # Cannot create/link without an email.

    # Link to an existing account with the same email, if one exists.
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        return {"user": existing, "is_new": False}

    # Otherwise create a new student account.
    username = email.split("@")[0]
    base_username = "".join(ch for ch in username if ch.isalnum())[:30] or "user"
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    new_user = User.objects.create_user(
        email=email,
        username=username,
        first_name=details.get("first_name") or "",
        last_name=details.get("last_name") or "",
        role=User.ROLE_STUDENT,
    )
    new_user.set_unusable_password()  # Social-only account; no password login.
    new_user.save()
    return {"user": new_user, "is_new": True}
