"""LabVault application entry point.

Creates the Flask application using the application factory and runs the
development server. Intended for local development only.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env if present (development only).
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Never enable debug mode in production. Controlled via FLASK_ENV.
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_ENV") == "development")
