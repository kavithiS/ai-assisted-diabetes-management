"""Inspect a PyTorch ZIP checkpoint without deserializing its pickle."""

import pickletools
import zipfile
from pathlib import Path

CHECKPOINT = (
    Path.home() / "Desktop" / "CGMacros_C2_processed" / "splits" / "gru_results" / "gru_best.pt"
)


def main() -> None:
    if not CHECKPOINT.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT}")

    with zipfile.ZipFile(CHECKPOINT) as archive:
        names = archive.namelist()
        metadata_files = [name for name in names if name.endswith("/data.pkl")]

        if len(metadata_files) != 1:
            raise ValueError(f"Expected one data.pkl file; found {metadata_files}")

        metadata = archive.read(metadata_files[0])

        print(f"Checkpoint: {CHECKPOINT}")
        print(f"Metadata file: {metadata_files[0]}")
        print(f"Metadata size: {len(metadata)} bytes")
        print("\nCheckpoint metadata instructions:")

        pickletools.dis(metadata)


if __name__ == "__main__":
    main()
