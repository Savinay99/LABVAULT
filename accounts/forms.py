"""Accounts app forms."""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm as DjangoPasswordChangeForm
from django.core.exceptions import ValidationError

from .models import User


class CustomAuthenticationForm(AuthenticationForm):
    """Login form authenticating by email instead of username."""

    username = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(
                self.request, username=email, password=password
            )
            if self.user_cache is None:
                raise ValidationError("Invalid email or password.")
            if not self.user_cache.is_active:
                raise ValidationError("Account is deactivated. Contact support.")
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class CustomUserCreationForm(forms.ModelForm):
    """Registration form."""

    password1 = forms.CharField(
        label="Password",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return password2

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.username = user.email  # USERNAME_FIELD is email, but username field still required
        user.role = User.ROLE_STUDENT
        if commit:
            user.save()
        return user

    def clean(self):
        cleaned = super().clean()
        # Delegate to Django's password validators.
        password1 = cleaned.get("password1")
        if password1:
            from django.contrib.auth.password_validation import validate_password
            try:
                validate_password(password1, self.instance)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


class PasswordChangeForm(DjangoPasswordChangeForm):
    """Password change form with Bootstrap-friendly widgets."""

    old_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    new_password1 = forms.CharField(
        label="New password",
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_new_password2(self):
        new_password1 = self.cleaned_data.get("new_password1")
        new_password2 = self.cleaned_data.get("new_password2")
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise ValidationError("Passwords do not match.")
        return new_password2
