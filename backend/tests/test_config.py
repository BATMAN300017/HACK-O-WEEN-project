import pytest

from app.core.config import DEVELOPMENT_SECRET_KEY, settings, validate_production_secret_key
from app.core.database import get_db_path


def test_development_can_use_the_demo_secret():
    validate_production_secret_key("development", DEVELOPMENT_SECRET_KEY)


@pytest.mark.parametrize(
    "secret_key",
    [
        DEVELOPMENT_SECRET_KEY,
        "replace-this-with-a-random-secret-before-deployment",
        "too-short",
        " " * 40,
    ],
)
def test_production_rejects_default_placeholder_and_weak_secrets(secret_key):
    with pytest.raises(RuntimeError, match="unique SECRET_KEY"):
        validate_production_secret_key("production", secret_key)


def test_production_accepts_a_unique_secret_of_sufficient_length():
    validate_production_secret_key("production", "a-unique-production-secret-with-adequate-length")


def test_unsupported_database_url_fails_instead_of_silently_using_sqlite(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://localhost/sentinelflow")

    with pytest.raises(ValueError, match="Only SQLite"):
        get_db_path()
