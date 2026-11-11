"""Django test configuration."""

import os
import sys

import django
import pytest

# Ensure the project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labvault_project.settings")
django.setup()


@pytest.fixture
def client():
    from django.test import Client
    return Client()
