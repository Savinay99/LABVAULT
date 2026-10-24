# Security — LabVault

## Implemented Controls

| Control | Implementation |
|---------|---------------|
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` (pbkdf2:sha256) |
| No plaintext passwords | Passwords never stored or logged |
| Unique email | UNIQUE constraint + pre-check |
| Generic auth failures | Same message for wrong email or wrong password |
| Rate limiting | Configurable failed-attempt lockout (see `config.py`) |
| Session security | HttpOnly, SameSite cookies; Secure in HTTPS; expiration |
| Session regeneration | Session cleared and rebuilt after login |
| CSRF protection | Flask-WTF tokens on all state-changing forms |
| Authorization | Role-based + ownership checks server-side on every protected operation |
| Deny by default | Anonymous users get 403 on protected routes |
| SQL injection | All queries parameterized via pyodbc `?` placeholders |
| XSS | `escape_html` output escaping; Content Security Policy |
| Malicious uploads | Extension allowlist, MIME signature check, size limit |
| Path traversal | Server-generated random storage keys; no user input in paths |
| Executable serving | `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` |
| Security headers | CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS (HTTPS) |
| No secrets in code | Environment variables only; `.env.example` placeholders |
| No debug in production | `DEBUG=False` in ProductionConfig |
| Audit logging | Administrative actions recorded in `AuditLogs` |

## Security Headers (applied on every response)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; ...
```

## Limitations

- Azure SQL Database and Azure Blob Storage credentials are not present in this environment; infrastructure security (TLS, encryption at rest) relies on Azure platform capabilities.
- Login rate limiting is configured but enforced at the application layer via `AuthError` guidance; a production deployment should also use a reverse-proxy rate limiter.
- Email verification and password reset are not implemented (SMTP not configured).
- No application-level encryption of file contents; relies on Azure SQL encryption at rest.

## Deployment Requirements

- HTTPS in production (`SESSION_COOKIE_SECURE=true`).
- Strong `FLASK_SECRET_KEY` from environment.
- Database credentials via environment variables, never committed.
- `debug` mode disabled in production.