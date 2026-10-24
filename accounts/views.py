"""Accounts app views: login, logout, register, profile, password change."""

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import CustomAuthenticationForm, CustomUserCreationForm, PasswordChangeForm


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
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, "Signed in successfully.")
            return redirect(_safe_next(request))
        messages.error(request, "Invalid email or password.")
    else:
        form = CustomAuthenticationForm(request)
    return render(request, "auth/login.html", {"form": form, "next": _safe_next(request)})


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
    return render(request, "auth/register.html", {"form": form})


@login_required
def profile_view(request):
    """View the current user's profile."""
    return render(request, "profile/view.html", {"user": request.user})


@login_required
def settings_view(request):
    """Change the current user's password."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password changed successfully.")
            return redirect("accounts:profile")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "profile/settings.html", {"form": form, "user": request.user})
