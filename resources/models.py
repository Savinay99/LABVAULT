"""Resources app models: Category, Subject, Resource, ResourceSubject."""

from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "Categories"
        ordering = ["name"]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Subject(models.Model):
    subject_code = models.CharField(max_length=20, unique=True)
    subject_name = models.CharField(max_length=100)

    class Meta:
        db_table = "Subjects"
        ordering = ["subject_code"]
        verbose_name = "subject"
        verbose_name_plural = "subjects"

    def __str__(self):
        return f"{self.subject_code} — {self.subject_name}"


class Resource(models.Model):
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    storage_key = models.CharField(max_length=200, unique=True)
    original_filename = models.CharField(max_length=260)
    content_type = models.CharField(max_length=100)
    file_size_bytes = models.BigIntegerField()
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Resources"
        ordering = ["-created_at"]
        verbose_name = "resource"
        verbose_name_plural = "resources"
        indexes = [
            models.Index(fields=["-created_at"], name="IX_Resources_CreatedAt"),
            models.Index(fields=["uploaded_by"], name="IX_Resources_UploadedBy"),
            models.Index(fields=["category"], name="IX_Resources_Category"),
            models.Index(fields=["visibility"], name="IX_Resources_Visibility"),
            models.Index(fields=["title"], name="IX_Resources_Title"),
            models.Index(
                fields=["uploaded_by", "-created_at"],
                name="IX_ResUpBy_CreatedAt",
            ),
        ]

    @property
    def file_size_formatted(self):
        """Human-readable file size."""
        try:
            size = int(self.file_size_bytes)
        except (TypeError, ValueError):
            return self.file_size_bytes
        for unit in ("bytes", "KB", "MB", "GB", "TB"):
            if abs(size) < 1024.0:
                return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @property
    def is_owner(self, user):
        return self.uploaded_by_id == getattr(user, "pk", None)

    def __str__(self):
        return self.title


class ResourceSubject(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        db_table = "ResourceSubjects"
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "subject"], name="unique_resource_subject"
            )
        ]
        indexes = [
            models.Index(fields=["subject"], name="IX_ResourceSubjects_SubjectId"),
            models.Index(fields=["resource"], name="IX_ResourceSubjects_ResourceId"),
        ]

    def __str__(self):
        return f"{self.resource} - {self.subject}"


class AuditLog(models.Model):
    """Security-relevant and administrative actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "AuditLogs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="IX_AuditLogs_CreatedAt"),
            models.Index(fields=["actor"], name="IX_AuditLogs_Actor"),
        ]

    def __str__(self):
        return f"{self.action} ({self.entity_type} #{self.entity_id})"

