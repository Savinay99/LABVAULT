"""Core app URL configuration."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("about/", views.about_view, name="about"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("faculty-dashboard/", views.faculty_dashboard, name="faculty_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]
