"""Where the image data lives.

Set ``C1_DATA_DIR`` to the ``Images Datasets`` folder (the one that holds ``_curation`` and
``_processed``), or pass ``--data-dir`` to a command.
"""

import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR_ENV = "C1_DATA_DIR"


class DataDirError(RuntimeError):
    """The data folder is not set or does not exist."""


@dataclass(frozen=True, slots=True)
class DataPaths:
    """Paths inside the data folder. Nothing here is created or checked except ``root``."""

    root: Path

    @property
    def curation(self) -> Path:
        """Manifests, class map, caches and reports."""
        return self.root / "_curation"

    @property
    def processed(self) -> Path:
        """Resized training copies of the images."""
        return self.root / "_processed"

    @property
    def raw_manifest(self) -> Path:
        """Manifest built from the original datasets."""
        return self.curation / "image_manifest.csv"

    @property
    def clean_manifest(self) -> Path:
        """Manifest after broken files and leaking scene groups were marked."""
        return self.curation / "image_manifest_clean.csv"

    @property
    def processed_manifest(self) -> Path:
        """Clean manifest plus the resized-copy columns; read by training."""
        return self.curation / "processed_manifest.csv"

    @property
    def runs(self) -> Path:
        """Default folder for weights and run reports."""
        return self.curation / "training" / "runs"

    @property
    def food101(self) -> Path:
        """Original Food-101 download."""
        return self.root / "Food-101"

    def manifest(self) -> Path:
        """Return the most processed manifest that exists."""
        for path in (self.processed_manifest, self.clean_manifest, self.raw_manifest):
            if path.is_file():
                return path
        raise DataDirError(f"No manifest found in {self.curation}")

    def food101_split_dir(self) -> Path:
        """Official Food-101 split lists if present, else the reconstructed ones."""
        official = self.food101 / "meta"
        if (official / "train.txt").is_file():
            return official
        return self.curation / "food101_split"

    def food101_image_dir(self) -> Path:
        """Resized Food-101 copies if present, else the originals."""
        resized = self.processed / "food101"
        return resized if resized.is_dir() else self.food101 / "images"


def data_paths(data_dir: str | Path | None = None) -> DataPaths:
    """Resolve the data folder from ``data_dir`` or the ``C1_DATA_DIR`` environment variable."""
    value = data_dir if data_dir else os.environ.get(DATA_DIR_ENV, "")
    if not value:
        raise DataDirError(
            f"Set {DATA_DIR_ENV} to the 'Images Datasets' folder, or pass --data-dir."
        )
    root = Path(value).expanduser()
    if not root.is_dir():
        raise DataDirError(f"Data folder does not exist: {root}")
    return DataPaths(root=root.resolve())
