"""Compatibility entry point for the Django application.

Prefer ``manage.py`` for Django management commands. With no arguments this
starts the local development server, matching the historical ``run.py`` UX.
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labvault_project.settings")
    from django.core.management import execute_from_command_line

    if len(sys.argv) == 1:
        sys.argv.extend(["runserver", "127.0.0.1:8000"])
    execute_from_command_line(sys.argv)
