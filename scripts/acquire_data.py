#!/usr/bin/env python3
"""Acquire or verify the exact raw datasets used by the T2DM pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen
import zipfile

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "data_sources.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "T2DM-reproducibility/1.0"})
    with urlopen(request) as response, destination.open("wb") as handle:
        while chunk := response.read(8 * 1024 * 1024):
            handle.write(chunk)


def _write_pidd(openml_csv: Path, destination: Path) -> None:
    with openml_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    output: list[str] = []
    labels = {"tested_positive": 1, "tested_negative": 0}
    for row in rows:
        output.append(
            ",".join(
                [
                    str(int(row["preg"])),
                    str(int(row["plas"])),
                    str(int(row["pres"])),
                    str(int(row["skin"])),
                    str(int(row["insu"])),
                    f'{float(row["mass"]):.1f}',
                    f'{float(row["pedi"]):.3f}',
                    str(int(row["age"])),
                    str(labels[row["class"]]),
                ]
            )
        )
    destination.write_text("\n".join(output), encoding="utf-8")


def _extract_member(archive: Path, member: str, destination: Path) -> None:
    with zipfile.ZipFile(archive) as package:
        matches = [name for name in package.namelist() if name.strip() == member]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one archive member {member!r}, found {matches}")
        with package.open(matches[0]) as source, destination.open("wb") as target:
            while chunk := source.read(8 * 1024 * 1024):
                target.write(chunk)


def _convert_brfss(archive: Path, member: str, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="t2dm-brfss-") as directory:
        xpt_path = Path(directory) / member
        _extract_member(archive, member, xpt_path)
        frame = pd.read_sas(xpt_path, format="xport")
        frame.to_csv(destination, index=False)


def verify_one(name: str, cfg: dict[str, object]) -> bool:
    path = ROOT / str(cfg["expected_path"])
    actual = sha256(path) if path.exists() else None
    expected = str(cfg["expected_sha256"])
    ok = actual == expected
    print(f"{name}: {'OK' if ok else 'MISSING_OR_MISMATCH'} path={path} sha256={actual}")
    return ok


def acquire_one(name: str, cfg: dict[str, object], *, force: bool) -> None:
    destination = ROOT / str(cfg["expected_path"])
    if destination.exists() and verify_one(name, cfg):
        return
    if destination.exists() and not force:
        raise RuntimeError(
            f"Refusing to replace mismatched {destination}; inspect it or pass --force"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"t2dm-{name}-") as directory:
        temporary_root = Path(directory)
        download = temporary_root / "download"
        candidate = temporary_root / destination.name
        _download(str(cfg["download_url"]), download)
        archive_hash = cfg.get("archive_sha256")
        if archive_hash and sha256(download) != str(archive_hash):
            raise RuntimeError(f"{name}: downloaded archive SHA-256 mismatch")
        method = str(cfg["acquisition"])
        if method == "openml_reconstruction":
            _write_pidd(download, candidate)
        elif method == "zip_member":
            _extract_member(download, str(cfg["archive_member"]), candidate)
        elif method == "sas_transport_to_csv":
            _convert_brfss(download, str(cfg["archive_member"]), candidate)
        else:
            raise ValueError(f"Unsupported acquisition method: {method}")
        actual = sha256(candidate)
        if actual != str(cfg["expected_sha256"]):
            raise RuntimeError(
                f"{name}: converted file SHA-256 {actual} does not match the manifest"
            )
        os.replace(candidate, destination)
    if not verify_one(name, cfg):
        raise RuntimeError(f"{name}: post-install verification failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="all")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    datasets = dict(payload["datasets"])
    names = sorted(datasets) if args.dataset == "all" else [args.dataset]
    unknown = sorted(set(names) - set(datasets))
    if unknown:
        raise SystemExit(f"Unknown dataset(s): {unknown}")
    if args.download:
        for name in names:
            acquire_one(name, dict(datasets[name]), force=args.force)
    elif not all(verify_one(name, dict(datasets[name])) for name in names):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
