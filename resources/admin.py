"""Resources app admin registration."""

from django.contrib import admin

from .models import (
    AccessLog,
    AuditLog,
    Category,
    Instrument,
    InstrumentBooking,
    InstrumentIssue,
    InstrumentMaintenance,
    Resource,
    ResourceFiles,
    ResourceSubject,
    Subject,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("subject_code", "subject_name")
    search_fields = ("subject_code", "subject_name")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "uploaded_by",
        "visibility",
        "file_size_formatted",
        "created_at",
    )
    list_filter = ("visibility", "category", "created_at")
    search_fields = ("title", "original_filename", "uploaded_by__email")
    readonly_fields = ("storage_key", "created_at", "updated_at")

    def has_add_permission(self, request):
        # Upload through the application so the file and checksum stay in sync.
        return False

    def has_delete_permission(self, request, obj=None):
        # Delete through the application so the stored object is cleaned up.
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(
            actor=request.user,
            action="resource_updated" if change else "resource_created",
            entity_type="Resource",
            entity_id=obj.pk,
        )


@admin.register(ResourceSubject)
class ResourceSubjectAdmin(admin.ModelAdmin):
    list_display = ("resource", "subject")
    list_filter = ("subject",)


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("user", "resource", "accessed_at", "ip_address")
    list_filter = ("accessed_at",)
    search_fields = ("user__email", "resource__title")
    readonly_fields = tuple(field.name for field in AccessLog._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResourceFiles)
class ResourceFilesAdmin(admin.ModelAdmin):
    list_display = ("resource", "original_filename", "file_size_bytes", "sha256_checksum")
    search_fields = ("resource__title", "original_filename", "sha256_checksum")
    readonly_fields = tuple(field.name for field in ResourceFiles._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = (
        "asset_id",
        "name",
        "category",
        "department",
        "location",
        "status",
        "is_active",
    )
    list_filter = ("status", "department", "category", "is_active")
    search_fields = ("asset_id", "name", "model_number", "department", "location")
    readonly_fields = ("created_at",)
    list_editable = ("is_active",)

    def has_delete_permission(self, request, obj=None):
        # Instruments are retired/deactivated so booking history remains intact.
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(
            actor=request.user,
            action="instrument_updated" if change else "instrument_created",
            entity_type="Instrument",
            entity_id=obj.pk,
        )


@admin.register(InstrumentBooking)
class InstrumentBookingAdmin(admin.ModelAdmin):
    list_display = ("instrument", "user", "start_time", "end_time", "status")
    list_filter = ("status", "instrument__department")
    search_fields = ("instrument__asset_id", "instrument__name", "user__email")
    readonly_fields = (
        "instrument",
        "user",
        "start_time",
        "end_time",
        "purpose",
        "status",
        "created_at",
    )
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InstrumentIssue)
class InstrumentIssueAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "issued_by",
        "issued_at",
        "due_at",
        "is_overdue_display",
        "returned_at",
        "returned_by",
    )
    list_filter = ("returned_at", "due_at")
    search_fields = ("booking__instrument__asset_id", "booking__user__email")
    readonly_fields = tuple(field.name for field in InstrumentIssue._meta.fields)
    actions = None

    @admin.display(boolean=True, description="Overdue")
    def is_overdue_display(self, obj):
        return obj.is_overdue

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InstrumentMaintenance)
class InstrumentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ("instrument", "maintenance_type", "performed_date", "next_due_date", "passed_inspection")
    list_filter = ("maintenance_type", "passed_inspection", "performed_date")
    search_fields = ("instrument__asset_id", "instrument__name", "description")
    readonly_fields = tuple(field.name for field in InstrumentMaintenance._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity_type", "entity_id")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("actor__email", "action", "entity_type")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False
