"""Resources app views: library, upload, details, edit, delete, download."""

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import ResourceEditForm, ResourceUploadForm
from .models import Category, Resource, Subject
from .storage import (
    StorageError,
    detect_mime,
    generate_storage_key,
    get_storage_backend,
    validate_file,
)


def _user_can_view_resource(user, resource):
    if resource.visibility == Resource.VISIBILITY_PUBLIC:
        return True
    if not user.is_authenticated:
        return False
    if user.is_administrator:
        return True
    return resource.uploaded_by_id == user.pk


def _user_can_edit_resource(user, resource):
    if not user.is_authenticated:
        return False
    if user.is_administrator:
        return True
    return resource.uploaded_by_id == user.pk


@login_required
def library(request):
    """Resource library with search, filter, sort, pagination."""
    from django.db.models import Q

    user = request.user
    page = int(request.GET.get("page", 1) or 1)
    page_size = int(request.GET.get("page_size", 20) or 20)
    search = request.GET.get("search", "") or None
    category_id = request.GET.get("category_id") or None
    subject_id = request.GET.get("subject_id") or None
    sort = request.GET.get("sort", "created_at")
    direction = request.GET.get("direction", "DESC")

    # Whitelist sort columns/directions to prevent ordering injection.
    sort_columns = {"created_at": "created_at", "title": "title", "file_size": "file_size_bytes", "updated_at": "updated_at"}
    if direction.upper() == "ASC":
        order_by = sort_columns.get(sort, "created_at")
    else:
        order_by = "-" + sort_columns.get(sort, "created_at")

    # Base queryset: students see public + own; admins see everything.
    queryset = Resource.objects.select_related("category", "uploaded_by").prefetch_related("subjects")
    if not user.is_administrator:
        queryset = queryset.filter(
            Q(visibility=Resource.VISIBILITY_PUBLIC) | Q(uploaded_by=user)
        )
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if subject_id:
        queryset = queryset.filter(subjects__id=subject_id)

    queryset = queryset.distinct()
    total = queryset.count()
    offset = (page - 1) * page_size
    items = list(queryset.order_by(order_by)[offset:offset + page_size])

    total_pages = max(1, -(-total // page_size)) if total else 1
    categories = Category.objects.all()
    subjects = Subject.objects.all()

    context = {
        "resources": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "categories": categories,
        "subjects": subjects,
        "search": search or "",
        "category_id": int(category_id) if category_id else None,
        "subject_id": int(subject_id) if subject_id else None,
        "sort": sort,
        "direction": direction,
    }
    return render(request, "resources/library.html", context)


@login_required
def upload(request):
    """Upload a new resource."""
    if request.method == "POST":
        form = ResourceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                form.add_error(None, "A file is required.")
            else:
                try:
                    from .storage import get_storage_backend, validate_file, generate_storage_key
                    # Re-open the uploaded file stream for validation (Django's
                    # UploadedFile is file-like and supports seek/read).
                    file_stream = uploaded_file.file
                    ext, mime = validate_file(file_stream, uploaded_file.name)
                    storage_key = generate_storage_key(uploaded_file.name)
                    file_stream.seek(0, os.SEEK_END)
                    size_bytes = file_stream.tell()
                    file_stream.seek(0)

                    backend = get_storage_backend()
                    backend.save(file_stream, uploaded_file.name, storage_key)

                    try:
                        resource = form.save(commit=False)
                        resource.uploaded_by = request.user
                        resource.storage_key = storage_key
                        resource.original_filename = uploaded_file.name
                        resource.content_type = mime
                        resource.file_size_bytes = size_bytes
                        resource.save()
                        form.save_m2m()
                        messages.success(request, "Resource uploaded successfully.")
                        return redirect("resources:library")
                    except Exception:
                        # Roll back the file if the DB insert failed.
                        try:
                            backend.delete(storage_key)
                        except Exception:
                            pass
                        raise
                except StorageError as exc:
                    form.add_error("file", str(exc))
                except Exception:
                    messages.error(request, "Upload failed. Please try again.")
    else:
        form = ResourceUploadForm()

    categories = Category.objects.all()
    subjects = Subject.objects.all()
    return render(request, "resources/upload.html", {
        "form": form,
        "categories": categories,
        "subjects": subjects,
    })


@login_required
def details(request, pk):
    """Resource details page."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_view_resource(request.user, resource):
        return HttpResponseForbidden("Access denied to this resource.")
    return render(request, "resources/details.html", {"resource": resource})


@login_required
def edit(request, pk):
    """Edit resource metadata."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_edit_resource(request.user, resource):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = ResourceEditForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, "Resource updated.")
            return redirect("resources:details", pk=resource.pk)
    else:
        form = ResourceEditForm(instance=resource)

    categories = Category.objects.all()
    subjects = Subject.objects.all()
    current_subjects = list(resource.subjects.values_list("id", flat=True))
    return render(request, "resources/edit.html", {
        "form": form,
        "resource": resource,
        "categories": categories,
        "subjects": subjects,
        "current_subjects": current_subjects,
    })


@login_required
def delete(request, pk):
    """Delete a resource (POST only)."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_edit_resource(request.user, resource):
        return HttpResponseForbidden("Access denied.")

    storage_key = resource.storage_key
    resource.delete()  # cascade deletes ResourceSubjects
    # Best-effort file cleanup after DB delete.
    if storage_key:
        try:
            get_storage_backend().delete(storage_key)
        except Exception:
            pass
    messages.success(request, "Resource deleted.")
    return redirect("resources:library")


@login_required
def download(request, pk):
    """Download a resource file with authorization."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_view_resource(request.user, resource):
        return HttpResponseForbidden("Access denied to this resource.")

    storage_key = resource.storage_key
    backend = get_storage_backend()

    # Azure: issue short-lived SAS URL and redirect.
    from .storage import AzureBlobStorage
    if isinstance(backend, AzureBlobStorage):
        try:
            return redirect(backend.download_url(storage_key))
        except Exception:
            raise Http404("Unable to generate download URL.")

    # Local: stream the file with safe headers.
    file_obj = backend.open(storage_key)
    if file_obj is None:
        raise Http404("File not found.")
    response = FileResponse(
        file_obj,
        content_type=resource.content_type or "application/octet-stream",
        as_attachment=True,
        filename=resource.original_filename,
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{resource.original_filename}"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
