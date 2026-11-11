"""LabVault application factory.

Builds and configures the Flask application, registers extensions, blueprints,
and error handlers. Database connections are created per-request through the
repository layer (see app/repositories).
"""
import logging
import os

from flask import Flask, jsonify, render_template

from .config import config_by_name
from .extensions import csrf


def _filesizeformat(value):
    """Jinja filter: format bytes into a human-readable size."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0:
            return f"{value:.0f} {unit}" if unit == "bytes" else f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def create_app(config_name=None):
    """Application factory.

    Args:
        config_name: Configuration key ('development', 'production',
            'testing'). Defaults to the FLASK_ENV environment variable or
            'development'.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    config_by_name.get(config_name, config_by_name["default"]).init_app(app)

    # Jinja filters.
    app.jinja_env.filters["filesizeformat"] = _filesizeformat

    # Initialize extensions.
    csrf.init_app(app)

    # Configure structured logging (no secrets ever logged).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    # Register blueprints.
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.resources import resources_bp
    from .routes.profile import profile_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resources_bp, url_prefix="/resources")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Ensure storage directory exists (local development).
    _ensure_storage(app)

    # Register error handlers.
    register_error_handlers(app)

    # Security headers on every response.
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy: same-origin scripts/styles only, inline
        # styles disabled, images/fonts from self.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    app.logger.info("LabVault application created (config=%s)", config_name)
    return app


def _ensure_storage(app):
    storage_path = app.config.get("STORAGE_PATH")
    if storage_path:
        try:
            os.makedirs(storage_path, exist_ok=True)
        except OSError as exc:
            app.logger.warning("Could not create storage directory: %s", exc)


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(error):
        if _wants_json():
            return jsonify({"error": "forbidden", "message": "Access denied."}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        if _wants_json():
            return jsonify({"error": "not_found", "message": "Resource not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        if _wants_json():
            return jsonify({"error": "request_too_large", "message": "The uploaded file exceeds the maximum allowed size."}), 413
        flash("The uploaded file exceeds the maximum allowed size.", "error")
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Internal server error: %s", error)
        if _wants_json():
            return (
                jsonify(
                    {
                        "error": "internal_server_error",
                        "message": "An unexpected error occurred.",
                    }
                ),
                500,
            )
        return render_template("errors/500.html"), 500


def _wants_json():
    from flask import request

    return request.is_json or "application/json" in (
        request.headers.get("Accept", "")
    )
