"""Authentication, session, and current-user tests."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_session_token, utcnow
from app.main import app
from app.models.session import Session
from app.models.user import User


def _client() -> TestClient:
    return TestClient(app)


def _email() -> str:
    return f"user-{uuid.uuid4()}@example.com"


def _register(client: TestClient, email: str | None = None, password: str = "valid-pass-1") -> dict:
    payload_email = email or _email()
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Founder", "email": payload_email, "password": password},
    )
    return {"response": response, "email": payload_email, "password": password}


def test_register_valid() -> None:
    client = _client()
    result = _register(client)
    response = result["response"]
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == result["email"]
    assert body["user"]["name"] == "Ada Founder"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert settings.session_cookie_name in response.cookies


def test_register_duplicate_email() -> None:
    client = _client()
    email = _email()
    first = _register(client, email=email)
    assert first["response"].status_code == 201
    second = _register(client, email=email)
    assert second["response"].status_code == 409


def test_register_invalid_email() -> None:
    client = _client()
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Ada", "email": "not-an-email", "password": "valid-pass-1"},
    )
    assert response.status_code == 422


def test_register_password_validation() -> None:
    client = _client()
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Ada", "email": _email(), "password": "short"},
    )
    assert response.status_code == 422


def test_login_valid_credentials() -> None:
    client = _client()
    registered = _register(client)
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": registered["password"]},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == registered["email"]
    assert settings.session_cookie_name in response.cookies


def test_login_wrong_password() -> None:
    client = _client()
    registered = _register(client)
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": "wrong-password-1"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email() -> None:
    client = _client()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": _email(), "password": "valid-pass-1"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_authenticated() -> None:
    client = _client()
    registered = _register(client)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == registered["email"]
    assert "password" not in body
    assert "password_hash" not in body


def test_me_unauthenticated() -> None:
    client = _client()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_invalid_token() -> None:
    client = _client()
    client.cookies.set(settings.session_cookie_name, "not-a-real-session-token")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_session_and_token_not_stored(async_session_factory) -> None:
    client = _client()
    registered = _register(client)
    raw_token = client.cookies.get(settings.session_cookie_name)
    assert raw_token
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200

    async with async_session_factory() as session:
        stored = await session.execute(select(Session))
        hashes = [row.token_hash for row in stored.scalars().all()]
        assert raw_token not in hashes
        assert hash_session_token(raw_token) in hashes

        user = await session.execute(select(User).where(User.email == registered["email"]))
        db_user = user.scalar_one()
        payload = me.json()
        assert db_user.password_hash != payload.get("password_hash")
        assert "password_hash" not in payload
        dumped = str(payload)
        assert db_user.password_hash not in dumped


@pytest.mark.asyncio
async def test_expired_session_cannot_authenticate(async_session_factory) -> None:
    client = _client()
    _register(client)
    raw_token = client.cookies.get(settings.session_cookie_name)
    token_hash = hash_session_token(raw_token)

    async with async_session_factory() as session:
        result = await session.execute(select(Session).where(Session.token_hash == token_hash))
        db_session = result.scalar_one()
        db_session.expires_at = utcnow() - timedelta(minutes=1)
        await session.commit()

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_revoked_session_cannot_authenticate_and_logout_revokes(
    async_session_factory,
) -> None:
    client = _client()
    _register(client)
    raw_token = client.cookies.get(settings.session_cookie_name)
    token_hash = hash_session_token(raw_token)

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    async with async_session_factory() as session:
        result = await session.execute(select(Session).where(Session.token_hash == token_hash))
        db_session = result.scalar_one()
        assert db_session.revoked_at is not None

    client.cookies.set(settings.session_cookie_name, raw_token)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_unauthenticated_company_endpoints_return_401() -> None:
    client = _client()
    company_id = uuid.uuid4()
    assert client.get("/api/v1/companies").status_code == 401
    assert (
        client.post(
            "/api/v1/companies",
            json={"name": "Acme", "description": "x", "target_customer": "y", "stage": "mvp"},
        ).status_code
        == 401
    )
    assert client.get(f"/api/v1/companies/{company_id}").status_code == 401
    assert client.patch(f"/api/v1/companies/{company_id}", json={"name": "Nope"}).status_code == 401
    assert client.get(f"/api/v1/companies/{company_id}/members").status_code == 401
