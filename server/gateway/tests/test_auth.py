"""Login, tokens, rate limit, refresh rotation and account deletion (ADR 0005)."""

import io
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from sqlalchemy import select

from diacare_gateway import cli
from diacare_gateway.auth.tokens import create_access_token
from diacare_gateway.config import GatewaySettings
from diacare_gateway.db.base import Base
from diacare_gateway.db.models import AppUser, AuditEvent, Consent, RefreshToken
from diacare_shared.db import make_engine

# Same values as in conftest.py (test fixtures, not secrets).
JWT_SECRET = "unit-test-jwt-secret-that-is-long-enough!"
PASSWORD = "correct horse battery"
EMAIL = "demo@example.test"
GatewayFactory = Callable[..., Any]
REGISTRATION = {
    "email": "New.Patient@Example.test",
    "password": "a long enough password",
    "consent_version": "v1",
    "accept": True,
}


def post(gateway: Any, path: str, **body: Any) -> Any:
    return gateway.client.post(f"/api/v1{path}", json=body)


def test_login_gives_tokens_and_me_returns_the_user(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    user_id = gateway.add_user(display_name="Demo", is_demo=True)

    tokens = gateway.login()
    me = gateway.client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60
    assert me.status_code == 200
    assert me.json()["user_id"] == str(user_id)
    assert me.json()["email"] == EMAIL
    assert "password" not in me.text


def test_wrong_password_and_unknown_email_look_the_same(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    gateway.add_user()

    wrong = post(gateway, "/auth/login", email=EMAIL, password="not the password")
    unknown = post(gateway, "/auth/login", email="nobody@example.test", password=PASSWORD)

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"] == unknown.json()["error"]
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_is_blocked_after_five_failures_even_with_the_right_password(
    make_gateway: GatewayFactory,
) -> None:
    gateway = make_gateway()
    gateway.add_user()

    for _ in range(5):
        assert post(gateway, "/auth/login", email=EMAIL, password="nope").status_code == 401
    blocked = post(gateway, "/auth/login", email=EMAIL, password=PASSWORD)

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert "retry-after" in blocked.headers


def test_a_successful_login_clears_earlier_failures(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    gateway.add_user()

    for _ in range(4):
        post(gateway, "/auth/login", email=EMAIL, password="nope")
    gateway.login()
    for _ in range(4):
        assert post(gateway, "/auth/login", email=EMAIL, password="nope").status_code == 401


def test_inactive_user_cannot_log_in_or_use_an_existing_token(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    user_id = gateway.add_user()
    headers = gateway.bearer()

    gateway.deactivate(user_id)

    assert gateway.client.get("/api/v1/me", headers=headers).status_code == 401
    assert post(gateway, "/auth/login", email=EMAIL, password=PASSWORD).status_code == 401


def test_expired_forged_and_malformed_tokens_are_refused(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    user_id = gateway.add_user()
    settings: GatewaySettings = gateway.app.state.settings
    expired = create_access_token(
        settings, user_id, "patient", now=datetime.now(UTC) - timedelta(hours=1)
    )
    forged = jwt.encode(
        {
            "sub": str(user_id),
            "role": "admin",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "typ": "access",
        },
        "some-other-secret-that-is-also-long-enough",
        algorithm="HS256",
    )
    unsigned = jwt.encode({"sub": str(user_id), "typ": "access"}, key=None, algorithm="none")

    for token in (expired, forged, unsigned, "garbage"):
        response = gateway.client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401, token
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert (
        gateway.client.get("/api/v1/me", headers={"Authorization": "Basic abc"}).status_code == 401
    )


def test_refresh_rotates_and_a_reused_token_ends_every_session(
    make_gateway: GatewayFactory,
) -> None:
    gateway = make_gateway()
    gateway.add_user()
    first = gateway.login()

    second = post(gateway, "/auth/refresh", refresh_token=first["refresh_token"])
    assert second.status_code == 200
    assert second.json()["refresh_token"] != first["refresh_token"]

    reuse = post(gateway, "/auth/refresh", refresh_token=first["refresh_token"])
    assert reuse.status_code == 401

    # The reuse revoked the newer token too.
    assert (
        post(gateway, "/auth/refresh", refresh_token=second.json()["refresh_token"]).status_code
        == 401
    )
    factory = gateway.app.state.session_factory
    with factory() as session:
        events = list(session.scalars(select(AuditEvent.event)))
    assert "token_reuse" in events


def test_refresh_token_is_stored_only_as_a_hash(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    gateway.add_user()
    tokens = gateway.login()

    factory = gateway.app.state.session_factory
    with factory() as session:
        stored = session.scalars(select(RefreshToken.token_hash)).all()
        password_hash = session.scalar(select(AppUser.password_hash))

    assert tokens["refresh_token"] not in stored
    assert len(stored[0]) == 64
    assert password_hash.startswith("$argon2id$")


def test_unknown_expired_refresh_tokens_are_refused(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway(refresh_token_days=0)
    gateway.add_user()
    tokens = gateway.login()

    assert post(gateway, "/auth/refresh", refresh_token="never-issued").status_code == 401
    assert post(gateway, "/auth/refresh", refresh_token=tokens["refresh_token"]).status_code == 401


def test_logout_revokes_the_refresh_token(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    gateway.add_user()
    tokens = gateway.login()

    assert post(gateway, "/auth/logout", refresh_token=tokens["refresh_token"]).status_code == 204
    assert post(gateway, "/auth/logout", refresh_token=tokens["refresh_token"]).status_code == 204
    assert post(gateway, "/auth/refresh", refresh_token=tokens["refresh_token"]).status_code == 401


def test_registration_is_closed_by_default(make_gateway: GatewayFactory) -> None:
    response = post(make_gateway(), "/auth/register", **REGISTRATION)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REGISTRATION_CLOSED"


def test_registration_when_open_creates_a_user_and_consent(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway(registration_enabled=True)

    created = post(gateway, "/auth/register", **REGISTRATION)
    assert created.status_code == 201
    login = post(
        gateway, "/auth/login", email="new.patient@example.test", password=REGISTRATION["password"]
    )
    assert login.status_code == 200

    factory = gateway.app.state.session_factory
    with factory() as session:
        consent = session.scalars(select(Consent)).one()
        user = session.scalars(select(AppUser)).one()
    assert (consent.consent_version, consent.scope) == ("v1", "app_use")
    assert user.email == "new.patient@example.test"
    assert user.role == "patient" and user.is_demo is False


def test_registration_rejects_duplicates_weak_passwords_and_missing_consent(
    make_gateway: GatewayFactory,
) -> None:
    gateway = make_gateway(registration_enabled=True)
    assert post(gateway, "/auth/register", **REGISTRATION).status_code == 201

    duplicate = post(
        gateway, "/auth/register", **{**REGISTRATION, "email": "new.patient@EXAMPLE.test"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_TAKEN"

    short = post(
        gateway,
        "/auth/register",
        **{**REGISTRATION, "email": "b@example.test", "password": "short"},
    )
    assert short.status_code == 422
    no_consent = post(
        gateway, "/auth/register", **{**REGISTRATION, "email": "c@example.test", "accept": False}
    )
    assert no_consent.status_code == 422
    bad_email = post(gateway, "/auth/register", **{**REGISTRATION, "email": "not-an-email"})
    assert bad_email.status_code == 422


def test_login_endpoints_say_so_when_no_database_is_configured(
    make_gateway: GatewayFactory,
) -> None:
    gateway = make_gateway(gateway_database_url=None)

    response = post(gateway, "/auth/login", email=EMAIL, password=PASSWORD)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_audit_events_hold_no_secrets(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    gateway.add_user()
    post(gateway, "/auth/login", email=EMAIL, password="nope")
    gateway.login()

    factory = gateway.app.state.session_factory
    with factory() as session:
        rows = list(session.scalars(select(AuditEvent)))
    assert [r.event for r in rows] == ["login_failed", "login_ok"]
    assert all(r.ip_hash and len(r.ip_hash) == 64 for r in rows)
    assert all("testclient" not in (r.ip_hash or "") for r in rows)


def test_delete_account_removes_service_data_then_the_user(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway(handler=lambda request: httpx.Response(204))
    user_id = gateway.add_user()
    headers = gateway.bearer()

    response = gateway.client.delete("/api/v1/me", headers=headers)

    assert response.status_code == 204
    call = gateway.seen[0]
    assert call.method == "DELETE"
    assert call.url.path == f"/internal/v1/patients/{user_id}"
    assert call.headers["x-internal-token"] == "test-internal-token"
    factory = gateway.app.state.session_factory
    with factory() as session:
        assert session.scalars(select(AppUser)).all() == []
        assert session.scalars(select(RefreshToken)).all() == []
        events = session.scalars(select(AuditEvent)).all()
    assert [e.event for e in events][-1] == "account_deleted"
    assert events[-1].user_id is None
    assert post(gateway, "/auth/login", email=EMAIL, password=PASSWORD).status_code == 401


def test_failed_service_delete_keeps_the_account_so_the_call_can_be_repeated(
    make_gateway: GatewayFactory,
) -> None:
    outcome = {"status": 500}
    gateway = make_gateway(handler=lambda request: httpx.Response(outcome["status"]))
    user_id = gateway.add_user()
    tokens = gateway.login()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    failed = gateway.client.delete("/api/v1/me", headers=headers)

    assert failed.status_code == 502
    factory = gateway.app.state.session_factory
    with factory() as session:
        user = session.get(AppUser, user_id)
        assert user is not None and user.is_active is True
    # No new session can be started from the old refresh token ...
    assert post(gateway, "/auth/refresh", refresh_token=tokens["refresh_token"]).status_code == 401
    # ... but the same call succeeds once the service is healthy again.
    outcome["status"] = 204
    assert gateway.client.delete("/api/v1/me", headers=headers).status_code == 204
    with factory() as session:
        assert session.get(AppUser, user_id) is None


def test_cli_creates_a_demo_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'core.db').as_posix()}"
    engine = make_engine(url, "core")
    Base.metadata.create_all(engine)
    settings = GatewaySettings(_env_file=None, gateway_database_url=url)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr("sys.stdin", io.StringIO("a long enough password\n"))

    code = cli.main(["create-user", "--email", "Demo@Example.test", "--demo", "--password-stdin"])

    assert code == 0
    with engine.connect() as connection:
        row = connection.exec_driver_sql("SELECT email, role, is_demo FROM app_user").one()
    assert tuple(row) == ("demo@example.test", "patient", 1)


def test_cli_refuses_a_short_password_and_a_duplicate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    url = f"sqlite:///{(tmp_path / 'core.db').as_posix()}"
    Base.metadata.create_all(make_engine(url, "core"))
    settings = GatewaySettings(_env_file=None, gateway_database_url=url)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
    assert cli.main(["create-user", "--email", "a@example.test", "--password-stdin"]) == 2

    monkeypatch.setattr("sys.stdin", io.StringIO("a long enough password\n"))
    assert cli.main(["create-user", "--email", "a@example.test", "--password-stdin"]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("a long enough password\n"))
    assert cli.main(["create-user", "--email", "A@example.test", "--password-stdin"]) == 1
