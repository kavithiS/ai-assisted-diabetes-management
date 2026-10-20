from pathlib import Path

import pytest
from c1_training.paths import DATA_DIR_ENV, DataDirError, data_paths


def test_missing_setting_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DATA_DIR_ENV, raising=False)
    with pytest.raises(DataDirError, match=DATA_DIR_ENV):
        data_paths()


def test_missing_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(DataDirError, match="does not exist"):
        data_paths(tmp_path / "nope")


def test_env_var_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    paths = data_paths()
    assert paths.root == tmp_path.resolve()
    assert paths.curation == tmp_path.resolve() / "_curation"
    assert paths.runs == tmp_path.resolve() / "_curation" / "training" / "runs"


def test_argument_wins_over_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    assert data_paths(other).root == other.resolve()


def test_manifest_prefers_processed(tmp_path: Path) -> None:
    paths = data_paths(tmp_path)
    paths.curation.mkdir()
    with pytest.raises(DataDirError):
        paths.manifest()
    paths.raw_manifest.write_text("x", encoding="utf-8")
    assert paths.manifest() == paths.raw_manifest
    paths.clean_manifest.write_text("x", encoding="utf-8")
    assert paths.manifest() == paths.clean_manifest
    paths.processed_manifest.write_text("x", encoding="utf-8")
    assert paths.manifest() == paths.processed_manifest


def test_food101_falls_back_to_reconstructed_split(tmp_path: Path) -> None:
    paths = data_paths(tmp_path)
    assert paths.food101_split_dir() == paths.curation / "food101_split"
    official = paths.food101 / "meta"
    official.mkdir(parents=True)
    (official / "train.txt").write_text("a/1\n", encoding="utf-8")
    assert paths.food101_split_dir() == official
