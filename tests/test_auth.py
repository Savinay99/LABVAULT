"""Tests for authentication service with mocked database layer."""

from unittest.mock import patch, MagicMock



import pytest
from app.config import Config



from app.services import auth_service

from app.security.validation import normalize_email





class FakeConn:

    """Stand-in for a pyodbc connection used by the repository helpers."""





def _make_user_row(email="student@example.edu", active=1, role="student", password="securepass123"):

    from werkzeug.security import generate_password_hash

    return {

        "UserId": 1,

        "FullName": "Test Student",

        "Email": email,

        "PasswordHash": generate_password_hash(password),

        "Role": role,

        "IsActive": active,

    }





def test_register_success():

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.email_exists.return_value = False

        mock_ur.create.return_value = 42



        user = auth_service.register("Ada Lovelace", "ADA@example.edu", "securepass123")



        assert user["user_id"] == 42

        assert user["email"] == "ada@example.edu"

        mock_ur.create.assert_called_once()

        # Verify password hash was passed, not plaintext.

        args = mock_ur.create.call_args

        assert args[0][3] != "securepass123"  # password_hash arg index

        assert args[0][3].startswith(("pbkdf2:", "scrypt:", "argon2"))





def test_register_duplicate_email():

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.email_exists.return_value = True



        with pytest.raises(auth_service.AuthError) as exc:

            auth_service.register("Ada", "ada@example.edu", "securepass123")

        assert exc.value.status_code == 409

        assert "already exists" in exc.value.message





def test_authenticate_success():

    row = _make_user_row()

    row["PasswordHash"] = auth_service.generate_password_hash if False else None

    from werkzeug.security import generate_password_hash

    row["PasswordHash"] = generate_password_hash("securepass123")



    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_email.return_value = row



        user = auth_service.authenticate("ADA@example.edu", "securepass123")

        assert user["user_id"] == 1

        assert user["role"] == "student"





def test_authenticate_wrong_password():

    from werkzeug.security import generate_password_hash

    row = _make_user_row()

    row["PasswordHash"] = generate_password_hash("securepass123")



    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_email.return_value = row



        with pytest.raises(auth_service.AuthError):

            auth_service.authenticate("ada@example.edu", "wrongpassword")





def test_authenticate_inactive_account():

    row = _make_user_row(active=0)

    from werkzeug.security import generate_password_hash

    row["PasswordHash"] = generate_password_hash("securepass123")



    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_email.return_value = row



        with pytest.raises(auth_service.AuthError):

            auth_service.authenticate("ada@example.edu", "securepass123")





def test_authenticate_user_not_found():

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_email.return_value = None



        with pytest.raises(auth_service.AuthError):

            auth_service.authenticate("noone@example.edu", "securepass123")





def test_change_password_success():

    from werkzeug.security import generate_password_hash, check_password_hash

    row = _make_user_row(password="securepass123")



    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_id.return_value = row



        auth_service.change_password(1, "securepass123", "newpass12345")

        mock_ur.update_password.assert_called_once()

        # update_password(conn, user_id, password_hash) -> index [0][2]

        new_hash = mock_ur.update_password.call_args[0][2]

        assert check_password_hash(new_hash, "newpass12345")





def test_change_password_wrong_current():

    from werkzeug.security import generate_password_hash

    row = _make_user_row()

    row["PasswordHash"] = generate_password_hash("oldpass123")



    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_id.return_value = row



        with pytest.raises(auth_service.AuthError) as exc:

            auth_service.change_password(1, "wrongold", "newpass12345")

        assert "incorrect" in exc.value.message





def test_login_lockout_after_max_failed_attempts():
    import app.services.auth_service as auth_mod

    auth_mod._login_attempts.clear()

    email = "locked@example.edu"

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:
        conn = FakeConn()
        mock_tx.return_value.__enter__.return_value = conn
        mock_tx.return_value.__exit__.return_value = False
        mock_ur.get_by_email.return_value = None

        # First MAX failures are recorded (400); the (MAX+1)th is blocked (429).
        for _ in range(Config.LOGIN_MAX_FAILED_ATTEMPTS):
            with pytest.raises(auth_service.AuthError) as exc:
                auth_service.authenticate(email, "wrongpassword")
            assert exc.value.status_code == 400

        with pytest.raises(auth_service.AuthError) as exc:
            auth_service.authenticate(email, "wrongpassword")
        assert exc.value.status_code == 429


def test_login_unknown_account_records_failure():
    import app.services.auth_service as auth_mod

    auth_mod._login_attempts.clear()

    email = "ghost@example.edu"

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:
        conn = FakeConn()
        mock_tx.return_value.__enter__.return_value = conn
        mock_tx.return_value.__exit__.return_value = False
        mock_ur.get_by_email.return_value = None

        # Record MAX failures (each 400); the next one tips into lockout (429).
        for _ in range(Config.LOGIN_MAX_FAILED_ATTEMPTS):
            with pytest.raises(auth_service.AuthError) as exc:
                auth_service.authenticate(email, "wrongpassword")
            assert exc.value.status_code == 400

        with pytest.raises(auth_service.AuthError) as exc:
            auth_service.authenticate(email, "wrongpassword")
        assert exc.value.status_code == 429


def test_successful_login_clears_failures(monkeypatch):

    import app.services.auth_service as auth_mod



    auth_mod._login_attempts.clear()



    email = "clear@example.edu"

    from werkzeug.security import generate_password_hash



    # Record one failure.

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_email.return_value = None



        with pytest.raises(auth_service.AuthError):

            auth_service.authenticate(email, "wrongpassword")

    assert email in auth_mod._login_attempts



    # A successful login must clear the record.

    row = _make_user_row(email=email)

    row["PasswordHash"] = generate_password_hash("securepass123")

    with patch("app.services.auth_service.db_transaction") as mock_tx, \
         patch("app.services.auth_service.user_repository") as mock_ur:

        conn = FakeConn()

        mock_tx.return_value.__enter__.return_value = conn

        mock_tx.return_value.__exit__.return_value = False

        mock_ur.get_by_email.return_value = row



        user = auth_service.authenticate(email, "securepass123")

        assert user["user_id"] == 1

    assert email not in auth_mod._login_attempts

