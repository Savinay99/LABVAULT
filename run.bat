@echo off
title LabVault Development Server
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Follow the README setup steps first.
  exit /b 1
)

echo Starting LabVault at http://127.0.0.1:8000. Press Ctrl+C to stop.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000

