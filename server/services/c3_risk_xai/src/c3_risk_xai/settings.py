"""C3 service settings, read from environment variables (see docs/ci_pr_note.md)."""

from functools import lru_cache

from diacare_shared.config import BaseServiceSettings


class C3Settings(BaseServiceSettings):
    # Off by default. Only when true may `?debug=true` return the raw probability and the
    # band cut-offs. Patient responses never contain them (open item in CLAUDE.md).
    c3_research_mode: bool = False
    # Save assessments in the c3 Postgres schema (DATABASE_URL). Best-effort: when the
    # database is down the service still answers. Tests switch it off.
    c3_persistence: bool = True


@lru_cache
def get_settings() -> C3Settings:
    return C3Settings()
