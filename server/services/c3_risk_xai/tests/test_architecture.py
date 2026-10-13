"""Architecture rules, checked by reading the import statements of every file.

- ml/ (including dataprep/) is plain Python: no web framework, no HTTP client, and
  nothing from api/, services/ or schemas.
- Only services/ may import ml/. api/, main.py, schemas.py and settings.py may not.
- Nothing on the request path (services/, api/) imports ml.dataprep (offline code).
- The Streamlit demo is a client: it imports no c3_risk_xai code at all.
"""

import ast
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[1]
PACKAGE = SERVICE / "src" / "c3_risk_xai"


def imported_modules(path: Path) -> set[str]:
    """Absolute names of everything `path` imports (relative imports are resolved)."""
    inside = path.is_relative_to(PACKAGE)
    package_parts = ["c3_risk_xai", *path.parent.relative_to(PACKAGE).parts] if inside else []
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - node.level + 1]
                module = ".".join([*base, node.module] if node.module else base)
            else:
                module = node.module or ""
            found.add(module)
            found.update(f"{module}.{alias.name}" for alias in node.names)
    return found


def files(folder: Path) -> list[Path]:
    return sorted(folder.rglob("*.py"))


def violations(paths: list[Path], forbidden: tuple[str, ...]) -> list[str]:
    return [
        f"{p.relative_to(SERVICE)} imports {m}"
        for p in paths
        for m in sorted(imported_modules(p))
        if m == "" or any(m == f or m.startswith(f + ".") for f in forbidden)
    ]


def test_ml_is_plain_python() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "httpx",
        "requests",
        "c3_risk_xai.api",
        "c3_risk_xai.services",
        "c3_risk_xai.schemas",
        "c3_risk_xai.settings",
        "c3_risk_xai.main",
    )
    assert violations(files(PACKAGE / "ml"), forbidden) == []


@pytest.mark.parametrize(
    "path",
    [PACKAGE / "main.py", PACKAGE / "schemas.py", PACKAGE / "settings.py", *files(PACKAGE / "api")],
    ids=lambda p: p.name,
)
def test_only_services_import_ml(path: Path) -> None:
    assert violations([path], ("c3_risk_xai.ml",)) == []


def test_request_path_never_imports_offline_code() -> None:
    request_path = files(PACKAGE / "services") + files(PACKAGE / "api")
    assert violations(request_path, ("c3_risk_xai.ml.dataprep",)) == []


def test_demo_is_a_client() -> None:
    assert violations(files(SERVICE / "demo"), ("c3_risk_xai",)) == []
