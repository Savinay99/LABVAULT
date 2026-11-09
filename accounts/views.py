"""Accounts app views: login, logout, register, profile, password change."""

import os
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from social_django.models import UserSocialAuth

from .forms import CustomAuthenticationForm, CustomUserCreationForm, PasswordChangeForm
from .models import LoginAttempt


def _get_oauth_status():
    """Return dictionary indicating which social auth providers are actively configured."""
    return {
        "google": bool(os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")),
        "microsoft": bool(os.environ.get("SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY")),
        "github": bool(os.environ.get("SOCIAL_AUTH_GITHUB_KEY")),
    }


def _safe_next(request, default="core:dashboard"):
    """Return a safe redirect target from the `next` parameter."""
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return reverse(default)


def login_view(request):
    """Sign in with email and password."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        email = (request.POST.get("username") or "").strip().lower()[:254]
        ip_address = request.META.get("REMOTE_ADDR") or "0.0.0.0"
        locked = LoginAttempt.objects.filter(
            email=email,
            ip_address=ip_address,
            locked_until__gt=timezone.now(),
        ).exists() if email else False

        if locked:
            messages.error(request, "Invalid email or password.")
        elif form.is_valid():
            user = form.get_user()
            LoginAttempt.objects.filter(email=email).delete()
            auth_login(request, user)
            messages.success(request, "Signed in successfully.")
            return redirect(_safe_next(request))
        else:
            if email:
                _record_failed_login(email, ip_address)
            messages.error(request, "Invalid email or password.")
    else:
        form = CustomAuthenticationForm(request)
    return render(
        request,
        "auth/login.html",
        {
            "form": form,
            "next": _safe_next(request),
            "oauth_configured": _get_oauth_status(),
        },
    )


def _record_failed_login(email, ip_address):
    """Persist a failed login and lock the email/IP pair after the configured limit."""
    now = timezone.now()
    attempt, _ = LoginAttempt.objects.get_or_create(
        email=email,
        ip_address=ip_address,
    )
    with transaction.atomic():
        attempt = LoginAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.locked_until and attempt.locked_until <= now:
            attempt.failed_attempts = 0
            attempt.locked_until = None
        attempt.failed_attempts += 1
        if attempt.failed_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            attempt.locked_until = now + timedelta(
                seconds=settings.LOGIN_LOCKOUT_SECONDS
            )
        attempt.save(update_fields=["failed_attempts", "locked_until", "last_attempt_at"])


@require_POST
def logout_view(request):
    """Sign out and clear the session."""
    auth_logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("accounts:login")


def register_view(request):
    """Register a new account."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. Welcome to LabVault.")
            return redirect("accounts:login")
    else:
        form = CustomUserCreationForm()
    return render(
        request,
        "auth/register.html",
        {"form": form, "oauth_configured": _get_oauth_status()},
    )


@login_required
def profile_view(request):
    """View the current user's profile."""
    return render(request, "profile/view.html", {"user": request.user})


@login_required
def settings_view(request):
    """Change the current user's password and manage connected social accounts."""
    social_accounts = UserSocialAuth.objects.filter(user=request.user)
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password changed successfully.")
            return redirect("accounts:profile")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "profile/settings.html", {
        "form": form,
        "user": request.user,
        "social_accounts": social_accounts,
    })


@login_required
def disconnect_social(request, provider):
    """Remove a connected social account."""
    if request.method != "POST":
        return redirect("accounts:settings")
    try:
        social = UserSocialAuth.objects.get(user=request.user, provider=provider)
        social.delete()
        messages.success(request, f"{provider.title()} account disconnected.")
    except UserSocialAuth.DoesNotExist:
        messages.error(request, "Connected account not found.")
    return redirect("accounts:settings")


@login_required
def security_log_view(request):
    """View personal access and download audit history for compliance and non-repudiation."""
    from resources.models import AccessLog
    logs = AccessLog.objects.filter(user=request.user).select_related("resource").order_by("-accessed_at")[:50]
    return render(request, "profile/security_log.html", {
        "user": request.user,
        "logs": logs,
    })
