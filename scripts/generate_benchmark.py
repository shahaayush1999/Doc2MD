#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from benchmark_cases import (
    p12_pfas,
    p15_architecture,
    p17_clinical,
    p21_semiconductor,
    p23_native_recovery,
)
from benchmark_cases.common import REPO_ROOT


BUILDERS = (
    p12_pfas.build,
    p15_architecture.build,
    p17_clinical.build,
    p21_semiconductor.build,
    p23_native_recovery.build,
)


@contextmanager
def _generation_lock(temporary_root: Path):
    """Process-level lock so two generators cannot replace the same corpus."""
    temporary_root.mkdir(parents=True, exist_ok=True)
    lock_path = temporary_root / ".benchmark-generate.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another benchmark generator holds {lock_path.relative_to(REPO_ROOT)}") from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        os.fsync(handle.fileno())
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _validate_generated(root: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_benchmark.py"),
            "--benchmark",
            str(root),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Generated benchmark failed validation:\n{result.stdout}\n{result.stderr}")
    try:
        validation = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Benchmark validator returned invalid JSON:\n{result.stdout}\n{result.stderr}") from exc
    warnings = validation.get("warnings") or []
    if validation.get("ok") is not True or warnings:
        raise RuntimeError(
            f"Generated benchmark is not release-clean: errors={validation.get('errors')!r}; warnings={warnings!r}"
        )


def _generate_in_place(output_root: Path) -> dict:
    output_root = output_root.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    cases = [builder(output_root) for builder in BUILDERS]
    page_count = sum(int(case["pages"]) for case in cases)
    if len(cases) != 5 or page_count != 84:
        raise ValueError(f"Expected five cases and 84 pages; built {len(cases)} cases and {page_count} pages")

    manifest = {
        "schemaVersion": 2,
        "name": "Doc2MD",
        "suite": "official",
        "scoreName": "Doc2MD Native PDF Score",
        "inputProtocol": "native_pdf",
        "providerFileModePolicy": "Send the native PDF file to the provider and record the provider's documented PDF ingestion mode separately. Do not convert official inputs to page images in the harness.",
        "version": "1.0.0",
        "description": "An unsaturated mixed-modality benchmark for faithful PDF-to-Markdown reconstruction across long regulated packets, full-page scans, native text, visual evidence, source precedence, spatial relations, and genuine malformed office exports.",
        "caseCount": len(cases),
        "pageCount": page_count,
        "cases": cases,
    }
    _write_json(output_root / "manifest.json", manifest)
    return manifest


def _rewrite_manifest_root(staging_root: Path, final_root: Path) -> dict:
    manifest_path = staging_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    staging_prefix = staging_root.relative_to(REPO_ROOT).as_posix() + "/"
    final_prefix = final_root.relative_to(REPO_ROOT).as_posix() + "/"
    for case in manifest["cases"]:
        for field in ("pdf", "gold", "spec", "facts"):
            value = case[field]
            if not value.startswith(staging_prefix):
                raise RuntimeError(f"Unexpected staged manifest path for {case['id']} {field}: {value}")
            case[field] = final_prefix + value[len(staging_prefix) :]
    _write_json(manifest_path, manifest)
    return manifest


def generate(output_root: Path) -> dict:
    output_root = output_root.resolve()
    canonical_root = (REPO_ROOT / "benchmark").resolve()
    temporary_root = (REPO_ROOT / "tmp").resolve()
    try:
        relative = output_root.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"Output must remain inside the repository: {output_root}") from exc
    if output_root != canonical_root:
        try:
            output_root.relative_to(temporary_root)
        except ValueError as exc:
            raise ValueError("Output must be the canonical benchmark/ directory or a child of tmp/") from exc
        if output_root == temporary_root:
            raise ValueError("Refusing to replace the tmp/ root")
        with _generation_lock(temporary_root):
            return _generate_in_place(output_root)

    with _generation_lock(temporary_root):
        staging_root = temporary_root / f".benchmark-build-{uuid.uuid4().hex}"
        backup_root = temporary_root / f".benchmark-backup-{uuid.uuid4().hex}"
        failed_root = temporary_root / f".benchmark-failed-{uuid.uuid4().hex}"
        backup_created = False
        promotion_started = False
        committed = False
        try:
            _generate_in_place(staging_root)
            _validate_generated(staging_root)
            manifest = _rewrite_manifest_root(staging_root, canonical_root)
            if canonical_root.exists():
                canonical_root.rename(backup_root)
                backup_created = True
            staging_root.rename(canonical_root)
            promotion_started = True
            _validate_generated(canonical_root)
            # The new canonical corpus is committed once final validation passes.
            # Backup cleanup must never roll a valid commit back.
            committed = True
            if backup_root.exists():
                try:
                    shutil.rmtree(backup_root)
                except OSError as exc:
                    print(f"Warning: committed benchmark but could not remove {backup_root}: {exc}", file=sys.stderr)
            return manifest
        except BaseException:
            if not committed:
                # Rename a failed promotion out of the canonical path before
                # restoring the prior tree. This keeps the restore atomic.
                promoted_without_flag = not staging_root.exists() and canonical_root.exists()
                if canonical_root.exists() and (promotion_started or promoted_without_flag):
                    canonical_root.rename(failed_root)
                if backup_created and backup_root.exists() and not canonical_root.exists():
                    backup_root.rename(canonical_root)
                if failed_root.exists():
                    shutil.rmtree(failed_root)
            raise
        finally:
            if staging_root.exists():
                shutil.rmtree(staging_root)
            # Never delete backup_root here: if rollback itself was interrupted,
            # preserving the backup is safer than guessing which tree is valid.


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the deterministic Doc2MD benchmark suite")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmark",
        help="Canonical output directory (default: benchmark); tmp/ children are allowed for reproducibility checks",
    )
    args = parser.parse_args()
    manifest = generate(args.output)
    print(
        f"Generated {manifest['caseCount']} cases / {manifest['pageCount']} pages at "
        f"{args.output.resolve().relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
