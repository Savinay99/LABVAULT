# LabVault local development launcher. Create an administrator separately with
# `python manage.py createsuperuser`; this script never prints credentials.
Set-Location $PSScriptRoot

# This script is a local development launcher. Respect an explicit setting,
# but default to DEBUG for a local checkout without a complete .env file.
if ([string]::IsNullOrWhiteSpace($env:DJANGO_DEBUG)) {
    $env:DJANGO_DEBUG = "True"
}

$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Error "Python environment not found. Follow the README setup steps first."
    exit 1
}

Write-Host "Starting LabVault at http://127.0.0.1:8000 (Ctrl+C to stop)."
& $pythonPath manage.py runserver 127.0.0.1:8000

