"""Gateway settings. Values come from environment variables (see `.env.example`)."""

from functools import lru_cache
from uuid import UUID

from pydantic import field_validator

from diacare_shared.config import BaseServiceSettings


class GatewaySettings(BaseServiceSettings):
    c1_url: str = "http://localhost:8001"
    c2_url: str = "http://localhost:8002"
    c3_url: str = "http://localhost:8003"
    c4_url: str = "http://localhost:8004"
    #: Timeout for the slow call (C1 photo analysis). Everything else uses the default below.
    request_timeout_seconds: float = 65.0
    default_timeout_seconds: float = 15.0
    health_timeout_seconds: float = 2.0
    #: Request bodies above this are refused (a little above C1's 10 MiB image limit).
    max_request_bytes: int = 11 * 1024 * 1024

    # Login (ADR 0005).
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    #: Database of the `core` schema. Without it login endpoints answer 503.
    gateway_database_url: str | None = None
    #: No self sign-up before ethical clearance; demo accounts come from the command line.
    registration_enabled: bool = False
    #: When false, every request is treated as coming from `demo_patient_id` (until the app has
    #: a login screen). Never use false with real patients.
    auth_required: bool = True
    demo_patient_id: UUID | None = None
    login_max_failures: int = 5
    login_window_minutes: int = 15
    #: Services asked to delete a patient's data (comma separated: c1,c2,c3,c4). Add a service
    #: here once it has `DELETE /internal/v1/patients/{id}`.
    delete_fanout_services: str = "c1"
    #: Browser origins allowed to call the gateway (comma separated), e.g. the Flutter web
    #: build used for local browser checks. Empty means no CORS: the mobile app does not need it.
    cors_origins: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def _check_secret_length(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 bytes")
        return value

    def service_urls(self) -> dict[str, str]:
        """Map each service package name to its base URL."""
        return {
            "c1_food_nutrition": self.c1_url,
            "c2_glycemic_forecasting": self.c2_url,
            "c3_risk_xai": self.c3_url,
            "c4_foot_monitoring": self.c4_url,
        }

    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    def fanout_urls(self) -> dict[str, str]:
        """Base URL of each service listed in `delete_fanout_services`."""
        keys = {
            "c1": self.c1_url,
            "c2": self.c2_url,
            "c3": self.c3_url,
            "c4": self.c4_url,
        }
        wanted = [k.strip().lower() for k in self.delete_fanout_services.split(",") if k.strip()]
        unknown = [k for k in wanted if k not in keys]
        if unknown:
            raise ValueError(f"DELETE_FANOUT_SERVICES names unknown services: {unknown}")
        return {k: keys[k] for k in wanted}


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
