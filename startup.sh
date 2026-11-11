#!/bin/bash
set -e

# Install Microsoft ODBC Driver 18 for SQL Server if missing in the container image
if ! command -v odbcinst >/dev/null 2>&1 || ! odbcinst -q -d | grep -q "ODBC Driver 18 for SQL Server"; then
    echo "[LabVault startup] Installing unixODBC and ODBC Driver 18 for SQL Server..."
    apt-get update -qq
    apt-get install -y -qq curl gnupg2 apt-transport-https unixodbc unixodbc-dev
    mkdir -p /usr/share/keyrings
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor --yes -o /usr/share/keyrings/microsoft-prod.gpg
    . /etc/os-release
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/${VERSION_ID}/prod ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/mssql-release.list
    apt-get update -qq
    ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18
fi

echo "[LabVault startup] Collecting static assets..."
python manage.py collectstatic --noinput

echo "[LabVault startup] Starting Gunicorn WSGI server on port ${PORT:-8000}..."
exec gunicorn labvault_project.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
