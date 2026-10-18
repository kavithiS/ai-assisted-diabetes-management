"""Gateway fixtures: an app on in-memory SQLite whose calls to the services are faked.

All tokens, secrets and e-mail addresses here are TEST FIXTURES.
"""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from diacare_gateway.auth.users import create_user
from diacare_gateway.config import GatewaySettings
from diacare_gateway.db.base import Base
from diacare_gateway.db.models import AppUser
from diacare_gateway.main import create_app

INTERNAL_TOKEN = "test-internal-token"
JWT_SECRET = "unit-test-jwt-secret-that-is-long-enough!"
DEMO_PATIENT = uuid.UUID("00000000-0000-4000-8000-000000000001")
PASSWORD = "correct horse battery"


class Gateway:
    """A test client plus the requests the fake services received."""

    def __init__(self, client: TestClient, seen: list[httpx.Request]) -> None:
        self.client = client
        self.seen = seen
        self.app = client.app

    def add_user(self, email: str = "demo@example.test", **kwargs: Any) -> uuid.UUID:
        factory = self.app.state.session_factory  # type: ignore[attr-defined]
        with factory() as session:
            user = create_user(
                session, email=email, password=kwargs.pop("password", PASSWORD), **kwargs
            )
            session.commit()
            return user.id

    def deactivate(self, user_id: uuid.UUID) -> None:
        factory = self.app.state.session_factory  # type: ignore[attr-defined]
        with factory() as session:
            session.get(AppUser, user_id).is_active = False
            session.commit()

    def login(self, email: str = "demo@example.test", password: str = PASSWORD) -> dict[str, Any]:
        response = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return dict(response.json())

    def bearer(self, email: str = "demo@example.test") -> dict[str, str]:
        return {"Authorization": f"Bearer {self.login(email)['access_token']}"}


GatewayFactory = Callable[..., Gateway]


@pytest.fixture
def make_gateway() -> Iterator[GatewayFactory]:
    clients: list[TestClient] = []

    def factory(
        handler: Callable[[httpx.Request], httpx.Response] | None = None, **overrides: Any
    ) -> Gateway:
        values: dict[str, Any] = {
            "log_level": "WARNING",
            "jwt_secret": JWT_SECRET,
            "internal_token": INTERNAL_TOKEN,
            "gateway_database_url": "sqlite://",
        }
        values.update(overrides)
        settings = GatewaySettings(_env_file=None, **values)
        app = create_app(settings)
        if app.state.engine is not None:
            Base.metadata.create_all(app.state.engine)

        seen: list[httpx.Request] = []

        def default_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return (handler or default_handler)(request)

        # The app lifespan is not run by a plain TestClient, so set the client by hand.
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(recording))
        client = TestClient(app, follow_redirects=False)
        clients.append(client)
        return Gateway(client, seen)

    yield factory
    for client in clients:
        client.close()
