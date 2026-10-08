"""C1 Food Recognition & Nutritional Analysis service.

Research prototype. Not a diagnostic or clinically validated tool.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("c1-food-nutrition")
except PackageNotFoundError:  # pragma: no cover - only when running from an uninstalled tree
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
