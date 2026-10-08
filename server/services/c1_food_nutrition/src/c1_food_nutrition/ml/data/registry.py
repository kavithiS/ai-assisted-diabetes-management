"""Config-driven registry of training-dataset sources.

C1 uses secondary datasets only (ADR 0002): Food-101 as the baseline, other public sets
once their licences are checked. TODO(c1): loading is not implemented yet.
Each candidate is a ``DatasetSource`` selected by the ``kind`` field of
a YAML file in ``training/configs/data/``, so swapping datasets is a config change.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import yaml  # type: ignore[import-untyped]  # stubs are not in the root dev group
from pydantic import BaseModel, ConfigDict, Field


class DatasetSourceConfig(BaseModel):
    """Contents of a ``configs/data/*.yaml`` file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Human-readable dataset name.")
    kind: str = Field(description="Registry key selecting the loader implementation.")
    root: Path = Field(description="Dataset root directory (DVC-tracked, under data/).")
    description: str | None = None


class DatasetSource(Protocol):
    """A training-data source. Loading is implemented in Phase 1."""

    @property
    def config(self) -> DatasetSourceConfig:
        """The validated configuration this source was built from."""
        ...

    def describe(self) -> str:
        """Return a short human-readable summary."""
        ...


DatasetSourceFactory = Callable[[DatasetSourceConfig], DatasetSource]

_REGISTRY: dict[str, DatasetSourceFactory] = {}


def register_dataset_source(kind: str) -> Callable[[DatasetSourceFactory], DatasetSourceFactory]:
    """Register a dataset source factory under ``kind``."""

    def decorator(factory: DatasetSourceFactory) -> DatasetSourceFactory:
        if kind in _REGISTRY:
            raise ValueError(f"Dataset source kind {kind!r} is already registered")
        _REGISTRY[kind] = factory
        return factory

    return decorator


def registered_kinds() -> list[str]:
    """Return the registered dataset kinds, sorted."""
    return sorted(_REGISTRY)


def load_dataset_config(path: Path) -> DatasetSourceConfig:
    """Load and validate a dataset YAML config."""
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return DatasetSourceConfig.model_validate(raw)


def build_dataset_source(config: DatasetSourceConfig) -> DatasetSource:
    """Instantiate the dataset source selected by ``config.kind``."""
    try:
        factory = _REGISTRY[config.kind]
    except KeyError:
        raise ValueError(
            f"Unknown dataset kind {config.kind!r}; registered kinds: {registered_kinds()}"
        ) from None
    return factory(config)


class PendingDatasetSource:
    """Placeholder source: the config is valid, but loading is not implemented yet."""

    def __init__(self, config: DatasetSourceConfig) -> None:
        self._config = config

    @property
    def config(self) -> DatasetSourceConfig:
        """The validated configuration this source was built from."""
        return self._config

    def describe(self) -> str:
        """Return a short summary of the configured source."""
        return f"{self._config.name} ({self._config.kind}) at {self._config.root}"

    def load(self) -> None:
        """Not implemented until Phase 1 (dataset not finalised)."""
        raise NotImplementedError(
            f"Loading for dataset kind {self._config.kind!r} is not implemented yet (Phase 1)."
        )


@register_dataset_source("food101")
class Food101Source(PendingDatasetSource):
    """Public Food-101 dataset (candidate)."""


# TODO(c1): register sources for the public Sri Lankan food image sets (Kaggle, Roboflow)
# once their licences are checked. The old team-collected "sl_team" source was removed
# because C1 uses secondary datasets only (ADR 0002).
