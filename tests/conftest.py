"""LabVault test configuration and fixtures.

Database-dependent code is tested with mocks because Azure SQL Database
credentials are not available in this environment. Tests never run against
production data.
"""
import os
import sys

import pytest

# Ensure the project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def app():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
