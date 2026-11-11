@echo off
title LabVault Development Server
cd /d "%~dp0"

rem Local development default only; preserve an explicit environment setting.
if not defined DJANGO_DEBUG set "DJANGO_DEBUG=True"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Follow the README setup steps first.
  exit /b 1
)

echo Starting LabVault at http://127.0.0.1:8000. Press Ctrl+C to stop.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000

