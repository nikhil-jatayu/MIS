from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_ENV = dotenv_values(BACKEND_DIR.parent / ".env")

TEST_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or ROOT_ENV.get("TEST_DATABASE_URL")
    or "postgresql+psycopg://postgres:postgres@localhost:5432/MIS_test"
)

os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-for-tests-1234567890"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["COOKIE_SECURE"] = "false"
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ALEMBIC_DATABASE_URL"] = TEST_DATABASE_URL

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402


@lru_cache
def cached_hash(password: str) -> str:
    return hash_password(password)


def _recreate_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    if not url.database:
        raise RuntimeError("TEST_DATABASE_URL must include a database name")
    with psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        dbname="postgres",
        autocommit=True,
    ) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(url.database))
        )
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))


def _migrate() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def test_engine():
    _recreate_database()
    _migrate()
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        autoflush=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_factory(db):
    def make_user(
        *,
        role: UserRole = UserRole.USER,
        email: str = "user@jatayues.com",
        name: str = "Test User",
        password: str = "TestPass@123",
        must_change_password: bool = False,
        is_active: bool = True,
    ) -> User:
        user = User(
            name=name,
            email=email.lower(),
            role=role,
            password_hash=cached_hash(password),
            is_active=is_active,
            must_change_password=must_change_password,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return make_user


@pytest.fixture
def standard_users(user_factory):
    return {
        "super": user_factory(
            role=UserRole.SUPER_ADMIN,
            email="super@jatayues.com",
            name="Super Admin",
            password="SuperPass@123",
        ),
        "admin": user_factory(
            role=UserRole.ADMIN,
            email="admin@jatayues.com",
            name="Project Admin",
            password="AdminPass@123",
        ),
        "user": user_factory(
            role=UserRole.USER,
            email="member@jatayues.com",
            name="Project Member",
            password="MemberPass@123",
        ),
        "other": user_factory(
            role=UserRole.USER,
            email="other@jatayues.com",
            name="Other User",
            password="OtherPass@123",
        ),
        "tester": user_factory(
            role=UserRole.USER,
            email="tester@jatayues.com",
            name="QA Tester",
            password="TesterPass@123",
        ),
    }


@pytest.fixture
def login(client):
    def _login(email: str, password: str) -> dict[str, str]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def auth_headers(login, standard_users):
    return {
        "super": login("super@jatayues.com", "SuperPass@123"),
        "admin": login("admin@jatayues.com", "AdminPass@123"),
        "user": login("member@jatayues.com", "MemberPass@123"),
        "other": login("other@jatayues.com", "OtherPass@123"),
        "tester": login("tester@jatayues.com", "TesterPass@123"),
    }
