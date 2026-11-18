"""Download the BIS central bankers' speeches archive (~130 MB).

Source: https://www.bis.org/cbspeeches/download.htm

Usage:
    python -m mood_tracker.download          # skips the download if the file exists
    python -m mood_tracker.download --force  # fetch the latest version
"""

from __future__ import annotations

import argparse
import shutil
import urllib.request
from pathlib import Path

SPEECHES_URL = "https://www.bis.org/pages/download-central-bankers-speeches/speeches.zip"
RAW_ZIP = Path(__file__).resolve().parents[1] / "data" / "raw" / "speeches.zip"


def download(force: bool = False) -> Path:
    if RAW_ZIP.exists() and not force:
        print(f"Already downloaded: {RAW_ZIP}")
        return RAW_ZIP
    RAW_ZIP.parent.mkdir(parents=True, exist_ok=True)
    partial = RAW_ZIP.with_suffix(".zip.part")
    print(f"Downloading {SPEECHES_URL} ...")
    with urllib.request.urlopen(SPEECHES_URL) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(RAW_ZIP)
    print(f"Saved {RAW_ZIP.stat().st_size / 1e6:.0f} MB to {RAW_ZIP}")
    return RAW_ZIP


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="download even if the file exists")
    download(parser.parse_args().force)
