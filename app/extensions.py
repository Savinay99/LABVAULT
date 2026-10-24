"""Flask extensions initialized once and shared across the application."""
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
