"""Inspect checkpoint ZIP storage entries without deserializing pickle."""

import zipfile
from pathlib import Path

CHECKPOINT = (
    Path.home() / "Desktop" / "CGMacros_C2_processed" / "splits" / "gru_results" / "gru_best.pt"
)


def main() -> None:
    with zipfile.ZipFile(CHECKPOINT) as archive:
        for name in archive.namelist():
            if name.startswith("gru_best/data/"):
                info = archive.getinfo(name)
                with archive.open(name) as tensor_file:
                    sample = tensor_file.read(16)

                print(f"\nStorage: {name}")
                print(f"Size: {info.file_size} bytes")
                print(f"First 16 bytes (hex): {sample.hex()}")


if __name__ == "__main__":
    main()
