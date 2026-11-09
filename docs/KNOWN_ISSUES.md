# LabVault — Known Issues & System Notes

1. **Azure Blob Storage vs Local Protected Storage**: In local development without Azure credentials, storage defaults to `LocalProtectedStorage` writing to `media/`. Live Azure Blob Storage requires setting `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER_NAME` in `.env`.
2. **Social OAuth Providers**: Third-party OAuth (Google, GitHub, Microsoft) requires client credentials in `.env` to be activated; social login buttons are omitted to prevent broken redirects when unconfigured.
3. **Framer Directory**: The `Framer/` folder at project root is a macOS Electron binary (`Framer.app`) for UI prototyping; no agricultural or "farmer" code exists in the Django codebase.
4. **Out-of-Scope Pages**: Unfinished secondary pages (notifications, advanced audit log exporter, profile extras) are deferred per student review scope.

