"""Resource routes: library, upload, details, edit, delete, download."""
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
    send_file,
    current_app,
)

from app.services import resource_service, auth_service
from app.security import permissions
from app.security.validation import (
    validate_resource_title,
    validate_resource_description,
)
from app.repositories.db import db_transaction
from app.repositories import resource_repository

resources_bp = Blueprint("resources", __name__, template_folder="../../templates")


def _current_user():
    if not session.get("user_id"):
        return None
    return {
        "user_id": session["user_id"],
        "email": session.get("email"),
        "full_name": session.get("full_name"),
        "role": session.get("role"),
    }


def _user():
    if not session.get("user_id"):
        abort(403)
    return {
        "user_id": session["user_id"],
        "email": session.get("email"),
        "full_name": session.get("full_name"),
        "role": session.get("role"),
    }


@resources_bp.route("/library")
def library():
    user = _user()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    search = request.args.get("search", "") or None
    category_id = request.args.get("category_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    sort = request.args.get("sort", "CreatedAt")
    direction = request.args.get("direction", "DESC")

    with db_transaction() as conn:
        if user["role"] == permissions.ROLE_ADMIN:
            items, total = resource_repository.list_resources(
                conn, page=page, page_size=page_size, search=search,
                category_id=category_id, subject_id=subject_id,
                sort=sort, direction=direction,
            )
        else:
            items, total = resource_service._list_student_resources(
                conn, user["user_id"], page, page_size, search, category_id,
                subject_id, sort, direction,
            )
        categories = resource_repository.list_categories(conn)
        subjects = resource_repository.list_subjects(conn)

    total_pages = max(1, -(-total // page_size)) if total else 1
    return render_template(
        "resources/library.html",
        resources=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        categories=categories,
        subjects=subjects,
        search=search or "",
        category_id=category_id,
        subject_id=subject_id,
        sort=sort,
        direction=direction,
    )


@resources_bp.route("/upload", methods=["GET", "POST"])
def upload():
    user = _user()
    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        category_id = request.form.get("category_id", "")
        visibility = request.form.get("visibility", "private")
        subject_ids = request.form.getlist("subject_ids")
        file_storage = request.files.get("file")

        if not file_storage or file_storage.filename == "":
            flash("A file is required.", "error")
            return redirect(request.url)

        try:
            # Stream wrapper: service expects a file-like with .stream/.filename.
            class _File:
                def __init__(self, fs):
                    self.stream = fs
                    self.filename = fs.filename
                    self.content_type = fs.content_type

            resource_service.create_resource(
                user,
                title=title,
                description=description,
                category_id=category_id,
                visibility=visibility,
                subject_ids=subject_ids,
                file_storage=_File(file_storage),
            )
            flash("Resource uploaded successfully.", "success")
            return redirect(url_for("resources.library"))
        except resource_service.ResourceError as exc:
            flash(exc.message, "error")
        except Exception:
            flash("Upload failed. Please try again.", "error")

    with db_transaction() as conn:
        categories = resource_repository.list_categories(conn)
        subjects = resource_repository.list_subjects(conn)
    return render_template("resources/upload.html", categories=categories, subjects=subjects)


@resources_bp.route("/resource/<int:resource_id>")
def details(resource_id):
    user = _user()
    try:
        resource = resource_service.get_resource(user, resource_id)
    except resource_service.ResourceError as exc:
        flash(exc.message, "error")
        if exc.status_code == 403:
            abort(403)
        return redirect(url_for("resources.library"))
    with db_transaction() as conn:
        subjects = resource_repository.get_resource_subjects(conn, resource_id)
    resource["Subjects"] = subjects
    return render_template("resources/details.html", resource=resource)


@resources_bp.route("/resource/<int:resource_id>/edit", methods=["GET", "POST"])
def edit(resource_id):
    user = _user()
    with db_transaction() as conn:
        resource = resource_repository.get_resource(conn, resource_id)
    if resource is None:
        flash("Resource not found.", "error")
        return redirect(url_for("resources.library"))
    is_owner = str(user["user_id"]) == str(resource["UploadedBy"])
    is_admin = user["role"] == permissions.ROLE_ADMIN
    if not (is_owner or is_admin):
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        category_id = request.form.get("category_id", "")
        visibility = request.form.get("visibility", "private")
        subject_ids = request.form.getlist("subject_ids")
        try:
            resource_service.update_resource(
                user, resource_id, title, description, category_id,
                visibility, subject_ids,
            )
            flash("Resource updated.", "success")
            return redirect(url_for("resources.details", resource_id=resource_id))
        except resource_service.ResourceError as exc:
            flash(exc.message, "error")
        except Exception:
            flash("Update failed.", "error")

    with db_transaction() as conn:
        categories = resource_repository.list_categories(conn)
        subjects = resource_repository.list_subjects(conn)
        current_subjects = [str(s["SubjectId"]) for s in resource_repository.get_resource_subjects(conn, resource_id)]
    return render_template(
        "resources/edit.html",
        resource=resource,
        categories=categories,
        subjects=subjects,
        current_subjects=current_subjects,
    )


@resources_bp.route("/resource/<int:resource_id>/delete", methods=["POST"])
def delete(resource_id):
    user = _user()
    try:
        resource_service.delete_resource(user, resource_id)
        flash("Resource deleted.", "success")
    except resource_service.ResourceError as exc:
        flash(exc.message, "error")
        if exc.status_code == 403:
            abort(403)
    return redirect(url_for("resources.library"))


@resources_bp.route("/resource/<int:resource_id>/download")
def download(resource_id):
    user = _user()
    try:
        resource = resource_service.get_resource(user, resource_id)
    except resource_service.ResourceError as exc:
        flash(exc.message, "error")
        if exc.status_code == 403:
            abort(403)
        return redirect(url_for("resources.library"))

    storage_key = resource.get("StorageKey")
    original_filename = resource.get("OriginalFileName") or "download"
    content_type = resource.get("ContentType") or "application/octet-stream"

    from app.services.storage_service import get_storage_backend

    backend = get_storage_backend()

    # Azure: issue short-lived SAS URL and redirect.
    azure_url = getattr(backend, "download_url", None)
    if callable(azure_url):
        try:
            return redirect(azure_url(storage_key))
        except Exception:
            abort(500)

    # Local: stream the file with safe headers.
    file_obj = backend.open(storage_key)
    if file_obj is None:
        abort(404)
    response = send_file(
        file_obj,
        mimetype=content_type,
        as_attachment=True,
        download_name=original_filename,
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{original_filename}"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
