"""Resources app URLs."""

from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    path("library/", views.library, name="library"),
    path("upload/", views.upload, name="upload"),
    path("resource/<int:pk>/", views.details, name="details"),
    path("resource/<int:pk>/edit/", views.edit, name="edit"),
    path("resource/<int:pk>/delete/", views.delete, name="delete"),
    path("resource/<int:pk>/download/", views.download, name="download"),
]
