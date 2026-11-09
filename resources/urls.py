"""Resources app URLs."""

from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    path("library/", views.library, name="library"),
    path("departments/", views.departments_directory, name="departments"),
    path("instruments/", views.instruments_list, name="instruments"),
    path("instruments/<int:pk>/book/", views.book_instrument, name="book_instrument"),
    path("instrument-bookings/<int:pk>/action/", views.booking_action, name="booking_action"),
    path("instrument-bookings/<int:pk>/issue/", views.issue_booking, name="issue_booking"),
    path("instrument-issues/<int:pk>/return/", views.return_issue, name="return_issue"),
    path("instruments/<int:pk>/maintenance/", views.instrument_maintenance_view, name="instrument_maintenance"),
    path("verify/", views.verify_integrity, name="verify"),
    path("upload/", views.upload, name="upload"),
    path("submissions/", views.submissions_hub, name="submissions_hub"),
    path("submissions/<int:pk>/download/", views.download_submission, name="download_submission"),
    path("submissions/<int:pk>/grade/", views.grade_submission, name="grade_submission"),
    path("export/audit-log/", views.export_audit_log, name="export_audit_log"),
    path("export/equipment-report/", views.export_equipment_report, name="export_equipment_report"),
    path("resource/<int:pk>/", views.details, name="details"),
    path("resource/<int:pk>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("resource/<int:pk>/submit/", views.submit_lab_report, name="submit_lab_report"),
    path("resource/<int:pk>/edit/", views.edit, name="edit"),
    path("resource/<int:pk>/delete/", views.delete, name="delete"),
    path("resource/<int:pk>/download/", views.download, name="download"),
    path("notifications/", views.notifications, name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.notification_mark_read,
        name="notification_mark_read",
    ),
    path(
        "notifications/read-all/",
        views.notification_mark_all_read,
        name="notification_mark_all_read",
    ),
]
