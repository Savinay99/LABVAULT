"""Resources app admin registration."""

from django.contrib import admin

from .models import Category, Resource, ResourceSubject, Subject


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


@admin.register(ResourceSubject)
class ResourceSubjectAdmin(admin.ModelAdmin):
    list_display = ("resource", "subject")
    list_filter = ("subject",)
