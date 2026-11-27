"""Resources app models: Category, Subject, Resource, ResourceSubject."""

from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.db import models
from django.utils import timezone


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
        return f"{self.subject_code}  -  {self.subject_name}"


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
    subjects = models.ManyToManyField(
        Subject, through="ResourceSubject", related_name="resources", blank=True
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


class AccessLog(models.Model):
    """Records who downloaded which resource and when (FR-24, NFR-01)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE
    )
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "AccessLog"
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["-accessed_at"], name="IX_AccessLog_CreatedAt"),
            models.Index(fields=["user"], name="IX_AccessLog_UserId"),
            models.Index(fields=["resource"], name="IX_AccessLog_ResourceId"),
        ]

    def __str__(self):
        return f"{self.user} accessed {self.resource} at {self.accessed_at}"


class ResourceFiles(models.Model):
    """File/blob metadata split from Resource descriptive metadata (FR-17).

    One file per resource; the storage key, original filename, content type,
    size, and SHA-256 checksum live here so integrity can be verified
    independently of the resource record.
    """

    resource = models.OneToOneField(
        Resource, on_delete=models.CASCADE, primary_key=True
    )
    storage_key = models.CharField(max_length=200, unique=True)
    original_filename = models.CharField(max_length=260)
    content_type = models.CharField(max_length=100)
    file_size_bytes = models.BigIntegerField()
    sha256_checksum = models.CharField(max_length=64)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ResourceFiles"
        verbose_name = "resource file"
        verbose_name_plural = "resource files"
        indexes = [
            models.Index(fields=["storage_key"], name="IX_ResourceFiles_StorageKey"),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.sha256_checksum[:12]}...)"


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


class Notification(models.Model):
    """In-app notifications for users (resource actions, system alerts)."""

    NOTIF_INFO = "info"
    NOTIF_SUCCESS = "success"
    NOTIF_WARNING = "warning"
    NOTIF_DANGER = "danger"

    NOTIF_TYPE_CHOICES = [
        (NOTIF_INFO, "Info"),
        (NOTIF_SUCCESS, "Success"),
        (NOTIF_WARNING, "Warning"),
        (NOTIF_DANGER, "Danger"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_sent",
    )
    verb = models.CharField(max_length=255)
    target_url = models.CharField(max_length=500, blank=True)
    notif_type = models.CharField(
        max_length=20, choices=NOTIF_TYPE_CHOICES, default=NOTIF_INFO
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="IX_Notifications_CreatedAt"),
            models.Index(fields=["recipient", "is_read"], name="IX_Notifications_RecipientRead"),
        ]

    def __str__(self):
        return f"Notification for {self.recipient}: {self.verb}"




class Instrument(models.Model):
    """Laboratory equipment and instrument inventory."""

    STATUS_AVAILABLE = "available"
    STATUS_IN_USE = "in_use"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_RETIRED = "retired"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_IN_USE, "In Use"),
        (STATUS_MAINTENANCE, "Under Maintenance"),
        (STATUS_RETIRED, "Retired"),
    ]

    asset_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    model_number = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE
    )
    is_active = models.BooleanField(default=True)
    condition = models.CharField(max_length=100, default="Calibrated / Good Condition")
    last_calibrated = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Instruments"
        ordering = ["asset_id"]
        verbose_name = "instrument"
        verbose_name_plural = "instruments"

    def __str__(self):
        return f"{self.asset_id} - {self.name}"


class InstrumentBooking(models.Model):
    """Reservations for laboratory instruments with interval overlap conflict prevention."""

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    # Backwards-compatible alias for existing code/tests using the old name.
    STATUS_CONFIRMED = STATUS_APPROVED
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUS_ISSUED = "issued"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_ISSUED, "Issued"),
        (STATUS_COMPLETED, "Completed"),
    ]

    instrument = models.ForeignKey(
        Instrument, on_delete=models.CASCADE, related_name="bookings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instrument_bookings",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    purpose = models.CharField(max_length=300)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "InstrumentBookings"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["instrument", "start_time", "end_time"], name="IX_InstBook_Range"),
            models.Index(fields=["user"], name="IX_InstBook_User"),
            models.Index(fields=["status", "start_time"], name="IX_InstBook_StatusStart"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="instrument_booking_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.instrument.asset_id} booked by {self.user.email}"


class InstrumentIssue(models.Model):
    """Issue and return record for one approved instrument booking."""

    booking = models.OneToOneField(
        InstrumentBooking, on_delete=models.PROTECT, related_name="issue"
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="instrument_issues_given",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="instrument_returns_recorded",
        null=True,
        blank=True,
    )
    returned_at = models.DateTimeField(null=True, blank=True)
    return_condition = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "InstrumentIssues"
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["due_at", "returned_at"], name="IX_InstIssue_DueReturn"),
        ]

    @property
    def is_overdue(self):
        return self.returned_at is None and self.due_at < timezone.now()

    def __str__(self):
        return f"Issue for {self.booking.instrument.asset_id} ({self.booking.user.email})"



class LabSubmission(models.Model):
    """Student laboratory reports and practical experiment submissions."""

    STATUS_SUBMITTED = "submitted"
    STATUS_REVIEWED = "reviewed"
    STATUS_RESUBMISSION = "resubmission"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REVIEWED, "Reviewed & Verified"),
        (STATUS_RESUBMISSION, "Resubmission Required"),
    ]

    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="submissions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lab_submissions",
    )
    original_filename = models.CharField(max_length=260)
    storage_key = models.CharField(max_length=200, unique=True)
    file_size_bytes = models.BigIntegerField()
    sha256_checksum = models.CharField(max_length=64)
    student_notes = models.TextField(blank=True, max_length=1500)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED
    )
    grade = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    faculty_feedback = models.TextField(blank=True, max_length=1500)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "LabSubmissions"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["resource", "student"], name="IX_LabSub_ResourceStudent"),
            models.Index(fields=["student", "-submitted_at"], name="IX_LabSub_StudentDate"),
            models.Index(fields=["status"], name="IX_LabSub_Status"),
        ]

    @property
    def file_size_formatted(self):
        try:
            size = int(self.file_size_bytes)
        except (TypeError, ValueError):
            return self.file_size_bytes
        for unit in ("bytes", "KB", "MB", "GB"):
            if abs(size) < 1024.0:
                return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def __str__(self):
        return f"Submission for {self.resource.title} by {self.student.email}"


class InstrumentMaintenance(models.Model):
    """Maintenance, calibration checks, and repair history for lab instruments."""

    TYPE_CALIBRATION = "calibration"
    TYPE_ROUTINE = "routine_service"
    TYPE_REPAIR = "repair"
    TYPE_INSPECTION = "safety_inspection"
    TYPE_CHOICES = [
        (TYPE_CALIBRATION, "Calibration Check"),
        (TYPE_ROUTINE, "Routine Service"),
        (TYPE_REPAIR, "Repair / Parts Replacement"),
        (TYPE_INSPECTION, "Safety & Compliance Inspection"),
    ]

    instrument = models.ForeignKey(
        Instrument, on_delete=models.CASCADE, related_name="maintenance_records"
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logged_maintenance",
    )
    maintenance_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES, default=TYPE_ROUTINE
    )
    description = models.TextField(max_length=1500)
    performed_date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    passed_inspection = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "InstrumentMaintenance"
        ordering = ["-performed_date"]
        indexes = [
            models.Index(fields=["instrument", "-performed_date"], name="IX_InstMaint_Date"),
        ]

    def __str__(self):
        return f"{self.instrument.asset_id} - {self.get_maintenance_type_display()} on {self.performed_date}"


class ResourceBookmark(models.Model):
    """User-starred / bookmarked laboratory manuals and resources."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ResourceBookmarks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "resource"], name="unique_user_resource_bookmark"
            )
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="IX_ResBookmark_User"),
        ]

    def __str__(self):
        return f"{self.user.email} bookmarked {self.resource.title}"


class Programme(models.Model):
    """An official CU-UP programme in the academic learning catalogue."""

    LEVEL_UNDERGRADUATE = "undergraduate"
    LEVEL_POSTGRADUATE = "postgraduate"
    LEVEL_CHOICES = [
        (LEVEL_UNDERGRADUATE, "Undergraduate"),
        (LEVEL_POSTGRADUATE, "Postgraduate"),
    ]

    CURRICULUM_NOT_PUBLICLY_VERIFIED = "not_publicly_verified"
    CURRICULUM_PARTIALLY_VERIFIED = "partially_verified"
    CURRICULUM_VERIFIED = "verified"
    CURRICULUM_STATUS_CHOICES = [
        (CURRICULUM_NOT_PUBLICLY_VERIFIED, "Not publicly verified"),
        (CURRICULUM_PARTIALLY_VERIFIED, "Partially verified"),
        (CURRICULUM_VERIFIED, "Verified"),
    ]

    source_key = models.CharField(max_length=220, unique=True)
    official_title = models.CharField(max_length=255)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    school = models.CharField(max_length=120, blank=True)
    official_url = models.URLField(max_length=500)
    curriculum_url = models.URLField(max_length=500, blank=True)
    curriculum_status = models.CharField(
        max_length=32,
        choices=CURRICULUM_STATUS_CHOICES,
        default=CURRICULUM_NOT_PUBLICLY_VERIFIED,
    )
    curriculum_last_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "AcademicProgrammes"
        ordering = ["level", "school", "official_title"]
        indexes = [
            models.Index(fields=["level", "is_active"], name="IX_AcadProg_LevelActive"),
            models.Index(fields=["school"], name="IX_AcadProg_School"),
        ]

    def __str__(self):
        return self.official_title


class CurriculumSubject(models.Model):
    """A subject copied only from a publicly verified CU-UP curriculum."""

    programme = models.ForeignKey(
        Programme, on_delete=models.CASCADE, related_name="curriculum_subjects"
    )
    official_code = models.CharField(max_length=50, blank=True)
    subject_name = models.CharField(max_length=255)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)
    curriculum_url = models.URLField(max_length=500)
    sequence = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "CurriculumSubjects"
        ordering = ["programme", "year_of_study", "semester", "sequence", "subject_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["programme", "year_of_study", "semester", "subject_name"],
                name="UQ_CurrSub_ProgTermName",
            )
        ]
        indexes = [
            models.Index(
                fields=["programme", "year_of_study", "semester"],
                name="IX_CurrSub_ProgTerm",
            ),
        ]

    def __str__(self):
        term = f"Year {self.year_of_study or '—'} / Semester {self.semester or '—'}"
        return f"{self.programme.official_title}: {self.subject_name} ({term})"


class StudentAcademicProfile(models.Model):
    """A student's declared programme and current term, separate from catalogue coverage."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="academic_profile",
    )
    programme = models.ForeignKey(
        Programme, on_delete=models.PROTECT, related_name="student_profiles"
    )
    school = models.CharField(max_length=120, blank=True)
    year_of_study = models.PositiveSmallIntegerField()
    semester = models.PositiveSmallIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "StudentAcademicProfiles"

    def save(self, *args, **kwargs):
        if self.programme_id:
            self.school = self.programme.school
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.programme.official_title} · Year {self.year_of_study} · Semester {self.semester}"


class CatalogResource(models.Model):
    """A curated external or official link, separate from uploaded Resources."""

    SOURCE_CUUP_OFFICIAL = "cuup_official"
    SOURCE_EXTERNAL = "external_supplementary"
    SOURCE_LABVAULT = "labvault_study_guide"
    SOURCE_CLASS_CHOICES = [
        (SOURCE_CUUP_OFFICIAL, "Official CU-UP"),
        (SOURCE_EXTERNAL, "External supplementary"),
        (SOURCE_LABVAULT, "LabVault Study Guide"),
    ]

    TYPE_SYLLABUS = "syllabus"
    TYPE_OVERVIEW = "overview"
    TYPE_NOTES = "study_guide"
    TYPE_PRACTICAL = "practical_manual"
    TYPE_ASSIGNMENT = "assignment"
    TYPE_TEXTBOOK = "open_textbook"
    TYPE_COURSE = "online_course"
    TYPE_VIDEO = "video_lecture"
    TYPE_PROJECT = "project"
    TYPE_REVISION = "exam_revision"
    TYPE_OTHER = "other"
    RESOURCE_TYPE_CHOICES = [
        (TYPE_SYLLABUS, "Syllabus / curriculum"),
        (TYPE_OVERVIEW, "Course overview"),
        (TYPE_NOTES, "Study guide / notes"),
        (TYPE_PRACTICAL, "Practical / experiment"),
        (TYPE_ASSIGNMENT, "Assignment / practice"),
        (TYPE_TEXTBOOK, "Open textbook"),
        (TYPE_COURSE, "Online course"),
        (TYPE_VIDEO, "Video lecture"),
        (TYPE_PROJECT, "Project / case study"),
        (TYPE_REVISION, "Exam revision"),
        (TYPE_OTHER, "Other"),
    ]

    ACCESS_OPEN = "open"
    ACCESS_REGISTRATION = "registration"
    ACCESS_LIBRARY = "library_access"
    ACCESS_PAID = "paid"
    ACCESS_UNKNOWN = "unknown"
    ACCESS_CHOICES = [
        (ACCESS_OPEN, "Open access"),
        (ACCESS_REGISTRATION, "Registration required"),
        (ACCESS_LIBRARY, "Library access"),
        (ACCESS_PAID, "Paid access"),
        (ACCESS_UNKNOWN, "Access not verified"),
    ]

    REVIEW_PENDING = "pending_review"
    REVIEW_APPROVED = "approved"
    REVIEW_REJECTED = "rejected"
    REVIEW_CHOICES = [
        (REVIEW_PENDING, "Pending review"),
        (REVIEW_APPROVED, "Approved"),
        (REVIEW_REJECTED, "Rejected"),
    ]

    LINK_UNVERIFIED = "unverified"
    LINK_WORKING = "working"
    LINK_UNAVAILABLE = "unavailable"
    LINK_RESTRICTED = "restricted"
    LINK_STATUS_CHOICES = [
        (LINK_UNVERIFIED, "Not checked"),
        (LINK_WORKING, "Working"),
        (LINK_UNAVAILABLE, "Unavailable"),
        (LINK_RESTRICTED, "Restricted / access-limited"),
    ]

    source_key = models.CharField(max_length=220, unique=True)
    title = models.CharField(max_length=255)
    canonical_url = models.URLField(max_length=2000)
    canonical_url_digest = models.CharField(max_length=64, unique=True, editable=False)
    source_organization = models.CharField(max_length=160)
    resource_type = models.CharField(max_length=24, choices=RESOURCE_TYPE_CHOICES)
    source_class = models.CharField(max_length=32, choices=SOURCE_CLASS_CHOICES)
    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name="catalog_resources",
        null=True,
        blank=True,
    )
    curriculum_subjects = models.ManyToManyField(
        CurriculumSubject, related_name="catalog_resources", blank=True
    )
    language = models.CharField(max_length=40, blank=True)
    access_type = models.CharField(
        max_length=20, choices=ACCESS_CHOICES, default=ACCESS_UNKNOWN
    )
    review_status = models.CharField(
        max_length=20, choices=REVIEW_CHOICES, default=REVIEW_PENDING
    )
    link_status = models.CharField(
        max_length=16, choices=LINK_STATUS_CHOICES, default=LINK_UNVERIFIED
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "CatalogResources"
        ordering = ["source_organization", "title"]
        indexes = [
            models.Index(
                fields=["review_status", "is_active", "link_status"],
                name="IX_CatRes_Visible",
            ),
            models.Index(fields=["source_organization"], name="IX_CatRes_SourceOrg"),
            models.Index(fields=["resource_type"], name="IX_CatRes_Type"),
        ]

    def save(self, *args, **kwargs):
        parts = urlsplit(self.canonical_url.strip())
        scheme = parts.scheme.lower()
        hostname = (parts.hostname or "").lower()
        if scheme in {"http", "https"} and hostname:
            port = parts.port
            default_port = (scheme == "http" and port == 80) or (
                scheme == "https" and port == 443
            )
            netloc = hostname if not port or default_port else f"{hostname}:{port}"
            path = parts.path.rstrip("/") or "/"
            self.canonical_url = urlunsplit(
                (scheme, netloc, path, parts.query, "")
            )
        self.canonical_url_digest = sha256(self.canonical_url.encode("utf-8")).hexdigest()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                "canonical_url",
                "canonical_url_digest",
            }
        super().save(*args, **kwargs)

    @property
    def is_student_visible(self):
        return (
            self.review_status == self.REVIEW_APPROVED
            and self.link_status == self.LINK_WORKING
            and self.is_active
            and (self.programme is None or self.programme.is_active)
        )

    def __str__(self):
        return self.title
