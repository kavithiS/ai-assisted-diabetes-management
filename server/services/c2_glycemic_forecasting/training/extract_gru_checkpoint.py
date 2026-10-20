"""Safely inspect GRU tensor storage without importing PyTorch."""

import zipfile
from pathlib import Path

import numpy as np

CHECKPOINT = (
    Path.home() / "Desktop" / "CGMacros_C2_processed" / "splits" / "gru_results" / "gru_best.pt"
)

TENSOR_SHAPES = {
    0: (96, 6),  # GRU input weights
    1: (96, 32),  # GRU recurrent weights
    2: (96,),  # GRU input bias
    3: (96,),  # GRU recurrent bias
    4: (16, 32),  # Output-layer weights
    5: (16,),  # Output-layer bias
    6: (6,),  # Feature means
    7: (6,),  # Feature standard deviations
    8: (16,),  # Target means
    9: (16,),  # Target standard deviations
}


def main() -> None:
    if not CHECKPOINT.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT}")

    with zipfile.ZipFile(CHECKPOINT) as archive:
        byteorder = archive.read("gru_best/byteorder").decode().strip()
        if byteorder != "little":
            raise ValueError(f"Unexpected checkpoint byte order: {byteorder}")

        for tensor_id, shape in TENSOR_SHAPES.items():
            name = f"gru_best/data/{tensor_id}"
            raw = archive.read(name)

            values = np.frombuffer(raw, dtype="<f4")
            expected_count = int(np.prod(shape))

            if values.size != expected_count:
                raise ValueError(f"{name}: expected {expected_count} values, found {values.size}")

            tensor = values.reshape(shape)

            if not np.isfinite(tensor).all():
                raise ValueError(f"{name} contains non-finite values")

            print(f"{name}: shape={tensor.shape}, dtype={tensor.dtype}, finite=True")

            if tensor_id in (7, 9) and np.any(tensor <= 0):
                raise ValueError(f"{name} contains a non-positive standard deviation")

    print("All ten tensor storages passed structural checks.")


if __name__ == "__main__":
    main()
