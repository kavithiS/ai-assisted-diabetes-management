# mypy: ignore-errors
# Older ML code, not fully typed yet. Remove these two lines once it is (docs/ci_pr_note.md).
"""Download the South Asian datasets used for the C3 experiment.

Every file is saved under data/c3/raw/external/ (gitignored) and logged in
manifest.json with its source URL, size and SHA-256, so the provenance of each
number we report can be traced back to an exact file.

No open individual-level Sri Lankan dataset exists (SLDCS, SLHAS, WHO STEPS and
the Colombo Urban Study are all available on request only), so the real data
is from Bangladesh, the closest open South Asian population.

Run:
    uv run python server/services/c3_risk_xai/training/external_data.py
"""

import hashlib
import json
import urllib.request
from datetime import date

from c3_risk_xai.ml.config import CFG, abs_path

MENDELEY = "https://data.mendeley.com/public-files/datasets/"

# All CC BY 4.0 on Mendeley Data.
FILES = {
    # DiaBD (Data in Brief 2025, DOI 10.17632/m8cgwxs9s6.2): 5,288 adults, Bangladesh.
    "bangladesh_diabd.csv": (
        MENDELEY + "m8cgwxs9s6/files/4c109a9f-2462-4dce-b93c-5789168c5401/file_downloaded"
    ),
    # Type-2 Diabetes Dataset Bangladesh (DOI 10.17632/rn9m3zb7nt.1): 1,065 hospital patients.
    "bangladesh_t2d_clinical.csv": (
        MENDELEY + "rn9m3zb7nt/files/919e2aba-deba-4ccb-84a9-3839dda138d7/file_downloaded"
    ),
}


def download(url: str, dest) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "c3-risk-profiling research"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return {
        "file": dest.name,
        "url": url,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "downloaded": date.today().isoformat(),
    }


def main():
    out = abs_path(CFG["paths"]["raw_dir"])
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for filename, url in FILES.items():
        print(f"Downloading {filename} ...")
        manifest.append(download(url, out / filename))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Saved {len(manifest)} files and manifest.json to {out}")


if __name__ == "__main__":
    main()
