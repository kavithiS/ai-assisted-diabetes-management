"""Gateway settings. Service URLs come from environment variables (see `.env.example`)."""

from functools import lru_cache

from diacare_shared.config import BaseServiceSettings


class GatewaySettings(BaseServiceSettings):
    c1_url: str = "http://localhost:8001"
    c2_url: str = "http://localhost:8002"
    c3_url: str = "http://localhost:8003"
    c4_url: str = "http://localhost:8004"
    request_timeout_seconds: float = 30.0
    health_timeout_seconds: float = 2.0

    def service_urls(self) -> dict[str, str]:
        """Map each service package name to its base URL."""
        return {
            "c1_food_nutrition": self.c1_url,
            "c2_glycemic_forecasting": self.c2_url,
            "c3_risk_xai": self.c3_url,
            "c4_foot_monitoring": self.c4_url,
        }


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
