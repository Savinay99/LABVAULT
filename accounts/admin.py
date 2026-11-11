"""Accounts app admin registration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import LoginAttempt, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        # Deactivate accounts instead so their audit and ownership history remains.
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from resources.models import AuditLog

        AuditLog.objects.create(
            actor=request.user,
            action="user_updated" if change else "user_created",
            entity_type="User",
            entity_id=obj.pk,
        )


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("email", "ip_address", "failed_attempts", "last_attempt_at", "locked_until")
    list_filter = ("locked_until", "last_attempt_at")
    search_fields = ("email", "ip_address")
    readonly_fields = tuple(field.name for field in LoginAttempt._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False
