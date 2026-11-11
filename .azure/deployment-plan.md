# LabVault Azure SQL Deployment Plan

Status: App configuration prepared; Azure CLI reauthentication is required before checking region/quota or provisioning.

## Goal

Deploy the existing Django LabVault application using Azure SQL Database as its database, with a minimal secure Azure hosting setup and a smoke-tested staging URL.

## Architecture (provisional)

- Azure App Service on Linux for the Django web application (Python 3.12, low-cost B1 baseline; verify availability/cost before provisioning).
- Azure SQL Database for relational data, authenticated from App Service with system-assigned managed identity.
- Azure Blob Storage for uploaded resources and durable submissions; keep the container private and store its connection setting as a Key Vault reference if available.
- HTTPS-only App Service; production `DEBUG=False`, generated Django secret, explicit host/CSRF origins, and secure cookies.

## Pending verification

- Azure CLI: subscription `Azure for Students` (`4e6f0e38-a5c3-42d5-b8ed-427fb8286362`), tenant `dc406629-976e-46e9-bdc5-dec251985fea`; refresh token expired on 2026-11-09. Reauthenticate before any Azure resource reads or writes.
- Target region and quota/cost constraints.
- Django SQL Server driver/backend present (`mssql-django`, `pyodbc`); managed-identity SQL mode and production static-file settings are being prepared. Run migrations against a new Azure SQL database before first use.
- Persistent media-storage configuration and production security settings.
- Resource names, service tiers, and expected monthly cost; confirm quota and region after reauthentication.

No Azure resources have been created. Region, quota, Azure Entra identity, and pricing must be verified after sign-in. Azure deployment remains pending.

## Resume checklist

1. In PowerShell, run `az login --tenant dc406629-976e-46e9-bdc5-dec251985fea`, select **Azure for Students**, and confirm with `az account show`.
2. Check App Service Python runtime support, available India regions, subscription quota, existing resource names, and current pricing. Choose the region/SKUs only after those checks.
3. Create the Linux App Service, Azure SQL logical server/database, and private Blob container.
4. Enable the App Service system-assigned managed identity and grant it SQL access. Use a temporary schema-migration role to run `manage.py migrate`, then reduce the app identity to runtime data roles. Configure Blob credentials through a secure App Service setting or Key Vault reference.
5. Configure production settings (`DJANGO_DEBUG=False`, a generated `DJANGO_SECRET_KEY`, exact `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, `DB_AUTH_MODE=managed_identity`, SQL host/name, and Blob settings); run `collectstatic`.
6. Deploy the Django root project with App Service build automation enabled, check logs, browse `/accounts/login/`, verify static assets, create a disposable smoke-test account, and exercise one core workflow.
7. Verify migrations and role access on Azure SQL, storage upload/download on Blob, and HTTPS/session behavior. Record actual resources, costs, and outcomes in `LABVAULT_COMPLETION_REPORT.md`.

Do not treat the local SQLite migration check as Azure SQL schema verification. No production/staging database currently exists in this subscription workflow.
