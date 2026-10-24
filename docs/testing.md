# Testing — LabVault

## Test Suite

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Flask app fixture (testing config) |
| `tests/test_validation.py` | Input validation, email normalization, output escaping |
| `tests/test_auth.py` | Registration, login, password change (mocked DB) |
| `tests/test_repositories.py` | Parameterized query usage (fake connections) |
| `tests/test_routes.py` | Route availability, anonymous access denial, CSRF tokens |
| `tests/test_security.py` | SQL injection rejection, XSS escaping, upload restrictions |
| `tests/test_storage.py` | File extension, size, MIME signature, storage key generation |

## How to Run

```powershell
python -m pytest tests/
```

## Results (executed)

All 40 tests passed in the current environment (Python 3.14, Flask test client, mocked database layer).

## Test Scope Notes

- Tests do **not** require Azure SQL Database credentials.
- Database-backed integration tests against real Azure SQL are not run here; repository tests verify parameterized query construction with fake connections.
- No destructive tests run against production data.
- Tests that depend on external Azure infrastructure are documented as requiring that infrastructure; they are not claimed to pass without it.