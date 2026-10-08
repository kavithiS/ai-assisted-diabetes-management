from pathlib import Path

import pytest

from c1_food_nutrition.ml.data.registry import (
    DatasetSourceConfig,
    Food101Source,
    PendingDatasetSource,
    build_dataset_source,
    load_dataset_config,
    register_dataset_source,
    registered_kinds,
)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "training" / "configs" / "data"


@pytest.mark.parametrize(
    ("filename", "expected_type"),
    [("food101.yaml", Food101Source)],
)
def test_shipped_configs_select_their_source(filename: str, expected_type: type) -> None:
    source = build_dataset_source(load_dataset_config(CONFIG_DIR / filename))
    assert isinstance(source, expected_type)


def test_loading_is_not_implemented_yet() -> None:
    source = build_dataset_source(load_dataset_config(CONFIG_DIR / "food101.yaml"))
    assert isinstance(source, PendingDatasetSource)
    with pytest.raises(NotImplementedError):
        source.load()


def test_unknown_kind() -> None:
    config = DatasetSourceConfig(name="x", kind="nope", root=Path("data/raw/x"))
    with pytest.raises(ValueError, match="Unknown dataset kind"):
        build_dataset_source(config)


def test_duplicate_registration_rejected() -> None:
    assert "food101" in registered_kinds()
    with pytest.raises(ValueError, match="already registered"):
        register_dataset_source("food101")(Food101Source)
