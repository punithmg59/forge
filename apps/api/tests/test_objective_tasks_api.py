"""Focused tests for Task 6.4 objective task list endpoint."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"tasks-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201


def _create_company(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": "Task View Co",
            "description": "desc",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_list_objective_tasks_returns_empty_for_new_company() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    response = client.get(f"/api/v1/companies/{company['id']}/objective-tasks")
    assert response.status_code == 200
    assert response.json() == {"tasks": []}


def test_unauthenticated_objective_task_list_returns_401() -> None:
    client = _client()
    response = client.get(f"/api/v1/companies/{uuid.uuid4()}/objective-tasks")
    assert response.status_code == 401
