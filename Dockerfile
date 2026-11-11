FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

# Install Microsoft's signed Debian 12 repository and the ODBC 18 runtime.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        libgssapi-krb5-2 \
        passwd \
        unixodbc \
        unixodbc-dev; \
    mkdir -p /usr/share/keyrings; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc -o /tmp/microsoft.asc; \
    gpg --dearmor --output /usr/share/keyrings/microsoft-prod.gpg /tmp/microsoft.asc; \
    chmod 0644 /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18; \
    rm -f /tmp/microsoft.asc; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -c "import pyodbc; assert 'ODBC Driver 18 for SQL Server' in pyodbc.drivers()"

RUN groupadd --system labvault \
    && useradd --system --gid labvault --home-dir /app --create-home labvault \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R labvault:labvault /app

COPY --chown=labvault:labvault . .

USER labvault

EXPOSE 10000

# Collect static assets at startup, then replace the shell with Gunicorn.
# Database migrations are intentionally not part of image build or startup.
CMD ["sh", "startup.sh"]
