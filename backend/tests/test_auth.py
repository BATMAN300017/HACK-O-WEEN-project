import sqlite3

import pytest
from fastapi import HTTPException

from app.api import dependencies
from app.api.v1.auth import login
from app.core.security import hash_password
from app.schemas.auth import LoginRequest


@pytest.fixture
def user_database():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        ("user-1", "investigator", "Investigator", "investigator", hash_password("password"), 1),
    )
    connection.commit()
    yield connection
    connection.close()


def test_login_accepts_active_user_and_normalizes_username(user_database):
    response = login(LoginRequest(username=" Investigator ", password="password"), user_database)

    assert response["username"] == "investigator"
    assert response["access_token"]


def test_login_rejects_inactive_user(user_database):
    user_database.execute("UPDATE users SET is_active = 0 WHERE id = ?", ("user-1",))

    with pytest.raises(HTTPException) as error:
        login(LoginRequest(username="investigator", password="password"), user_database)

    assert error.value.status_code == 401


def test_login_rejects_wrong_password(user_database):
    with pytest.raises(HTTPException) as error:
        login(LoginRequest(username="investigator", password="incorrect"), user_database)

    assert error.value.status_code == 401


def test_existing_token_is_rejected_after_user_is_deactivated(user_database, monkeypatch):
    monkeypatch.setattr(dependencies, "decode_access_token", lambda _: {"sub": "user-1"})
    user_database.execute("UPDATE users SET is_active = 0 WHERE id = ?", ("user-1",))

    with pytest.raises(HTTPException) as error:
        dependencies.get_current_user("Bearer token", user_database)

    assert error.value.status_code == 401
