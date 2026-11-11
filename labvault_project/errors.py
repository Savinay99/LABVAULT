"""LabVault project-level error handlers and security headers."""

import logging

from django.shortcuts import render

logger = logging.getLogger(__name__)


def handler403(request, exception, template_name="errors/403.html"):
    return render(request, template_name, {"code": 403, "message": "Access denied."}, status=403)


def handler404(request, exception, template_name="errors/404.html"):
    return render(
        request,
        template_name,
        {"code": 404, "message": "The page you are looking for does not exist."},
        status=404,
    )


def handler413(request, exception, template_name="errors/413.html"):
    return render(
        request,
        template_name,
        {"code": 413, "message": "The uploaded file exceeds the maximum allowed size."},
        status=413,
    )


def handler500(request, template_name="errors/500.html"):
    logger.exception("Internal server error")
    return render(
        request,
        template_name,
        {"code": 500, "message": "An unexpected error occurred."},
        status=500,
    )
