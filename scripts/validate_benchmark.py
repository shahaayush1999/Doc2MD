#!/usr/bin/env python3
"""Validate Doc2MD benchmark artifacts before inference is allowed.

This validator deliberately checks source artifacts and scoring metadata together.
It is strict about schema integrity, page anchors, unexpanded templates, and
benchmark-facing language. Visual judgment still requires rendered-page review.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmark"

UNEXPANDED_PATTERNS = (
    re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*(?:\([^}\n]*\))?\}"),
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE),
)

# These tokens are not allowed in benchmark source documents. They may occur in
# evaluator metadata, so this scan is intentionally limited to extracted PDF text.
SOURCE_META_PATTERNS = (
    re.compile(r"\bbenchmark\b", re.IGNORECASE),
    re.compile(r"\bcandidate\b", re.IGNORECASE),
    re.compile(r"markdown output", re.IGNORECASE),
    re.compile(r"convert (?:this|the) .{0,30}markdown", re.IGNORECASE),
    re.compile(r"model output", re.IGNORECASE),
    re.compile(r"for (?:benchmark|model) evaluation", re.IGNORECASE),
    re.compile(r"extract (?:this|the)", re.IGNORECASE),
    re.compile(r"preserve .{0,50}because", re.IGNORECASE),
    re.compile(r"values? (?:are|is) not repeated", re.IGNORECASE),
)

SAFE_CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass
class Validation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cases: list[dict[str, Any]] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_json(path: Path, validation: Validation) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        validation.error(f"Missing JSON file: {path}")
    except json.JSONDecodeError as exc:
        validation.error(f"Invalid JSON in {path}: {exc}")
    except OSError as exc:
        validation.error(f"Cannot read JSON file {path}: {exc}")
    return None


def resolve_artifact(value: Any, field: str, case_id: str, validation: Validation) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        validation.error(f"{case_id}: manifest {field} must be a non-empty repository-relative path")
        return None
    raw = Path(value)
    path = (ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        validation.error(f"{case_id}: {field} escapes repository root: {value}")
        return None
    return path


def extract_pdf_text(reader: PdfReader) -> str:
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def inspect_pdf_layout(pdf: Path, case_id: str, validation: Validation) -> dict[str, int | float]:
    native_text_pages = 0
    image_pages = 0
    full_page_raster_pages = 0
    with pdfplumber.open(pdf) as document:
        for page_number, page in enumerate(document.pages, start=1):
            chars = page.chars
            if chars:
                native_text_pages += 1
            tiny = [char for char in chars if float(char.get("size", 0)) < 5.5 and str(char.get("text", "")).strip()]
            if tiny:
                validation.warn(
                    f"{case_id} p{page_number}: {len(tiny)} native text glyphs are smaller than 5.5 pt"
                )
            outside = [
                char
                for char in chars
                if float(char.get("x0", 0)) < -0.5
                or float(char.get("x1", 0)) > page.width + 0.5
                or float(char.get("top", 0)) < -0.5
                or float(char.get("bottom", 0)) > page.height + 0.5
            ]
            if outside:
                validation.error(f"{case_id} p{page_number}: {len(outside)} native glyphs fall outside the page")
            images = page.images
            if images:
                image_pages += 1
            for image in images:
                x0 = float(image.get("x0", 0))
                x1 = float(image.get("x1", 0))
                y0 = float(image.get("y0", 0))
                y1 = float(image.get("y1", 0))
                if x0 < -0.5 or x1 > page.width + 0.5 or y0 < -0.5 or y1 > page.height + 0.5:
                    validation.error(f"{case_id} p{page_number}: an image falls outside the page")
                srcsize = image.get("srcsize")
                width_points = max(0.0, x1 - x0)
                height_points = max(0.0, y1 - y0)
                if (
                    isinstance(srcsize, tuple)
                    and len(srcsize) == 2
                    and width_points > 0
                    and height_points > 0
                ):
                    effective_dpi = min(float(srcsize[0]) * 72 / width_points, float(srcsize[1]) * 72 / height_points)
                    if effective_dpi < 90:
                        validation.error(f"{case_id} p{page_number}: embedded image is only {effective_dpi:.0f} effective DPI")
                    elif effective_dpi < 120:
                        validation.warn(f"{case_id} p{page_number}: embedded image is only {effective_dpi:.0f} effective DPI")
            page_area = page.width * page.height
            if any(
                max(0.0, float(image.get("x1", 0)) - float(image.get("x0", 0)))
                * max(0.0, float(image.get("y1", 0)) - float(image.get("y0", 0)))
                >= page_area * 0.9
                for image in images
            ):
                full_page_raster_pages += 1
    return {
        "nativeTextPages": native_text_pages,
        "imagePages": image_pages,
        "fullPageRasterPages": full_page_raster_pages,
    }


def validate_gold(path: Path, case: dict[str, Any], validation: Validation) -> None:
    case_id = case["id"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        validation.error(f"{case_id}: cannot read gold {path}: {exc}")
        return
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if first_line != f"# {case['title']}":
        validation.error(f"{case_id}: gold H1 must exactly match the manifest title")
    for pattern in UNEXPANDED_PATTERNS:
        match = pattern.search(text)
        if match:
            validation.error(f"{case_id}: unexpanded/template text in gold: {match.group(0)!r}")


def validate_facts(path: Path, case: dict[str, Any], validation: Validation) -> tuple[int, int]:
    facts = load_json(path, validation)
    if not isinstance(facts, dict):
        return 0, 0
    if facts.get("schemaVersion") != 2:
        validation.error(f"{case['id']}: facts schemaVersion must be 2")
    if facts.get("id") != case["id"]:
        validation.error(f"{case['id']}: facts id mismatch")
    for field in ("title", "family", "tags"):
        if facts.get(field) != case.get(field):
            validation.error(f"{case['id']}: facts {field} does not match manifest")
    regions = facts.get("regions")
    if not isinstance(regions, list) or not regions:
        validation.error(f"{case['id']}: facts must contain non-empty regions[]")
        return 0, 0

    region_ids: set[str] = set()
    leaf_ids: set[str] = set()
    anchored_pages: set[int] = set()
    leaf_count = 0
    for region in regions:
        if not isinstance(region, dict):
            validation.error(f"{case['id']}: region is not an object")
            continue
        region_id = region.get("id")
        if not isinstance(region_id, str) or not region_id:
            validation.error(f"{case['id']}: region missing id")
            continue
        if region_id in region_ids:
            validation.error(f"{case['id']}: duplicate region id {region_id}")
        region_ids.add(region_id)
        page = region.get("page")
        if not isinstance(page, int) or not 1 <= page <= int(case["pages"]):
            validation.error(f"{case['id']}/{region_id}: page anchor {page!r} is out of range")
        else:
            anchored_pages.add(page)
        if region.get("budget") not in (1, 2):
            validation.error(f"{case['id']}/{region_id}: budget must be 1 or 2")
        if not isinstance(region.get("closedWorld"), bool):
            validation.error(f"{case['id']}/{region_id}: closedWorld must be boolean")
        if region.get("kind") not in {
            "text",
            "table",
            "chart",
            "diagram",
            "form",
            "image",
            "structure",
        }:
            validation.error(f"{case['id']}/{region_id}: unsupported kind {region.get('kind')!r}")
        leaves = region.get("leaves")
        if not isinstance(leaves, list) or not leaves:
            validation.error(f"{case['id']}/{region_id}: region has no leaves")
            continue
        for leaf in leaves:
            if not isinstance(leaf, dict):
                validation.error(f"{case['id']}/{region_id}: leaf is not an object")
                continue
            leaf_id = leaf.get("id")
            if not isinstance(leaf_id, str) or not leaf_id:
                validation.error(f"{case['id']}/{region_id}: leaf missing id")
                continue
            if leaf_id in leaf_ids:
                validation.error(f"{case['id']}: duplicate leaf id {leaf_id}")
            leaf_ids.add(leaf_id)
            leaf_count += 1
            expectation = leaf.get("expectation")
            if not isinstance(expectation, str) or len(expectation.strip()) < 4:
                validation.error(f"{case['id']}/{leaf_id}: expectation is empty")
            if leaf.get("harm") not in (1, 2):
                validation.error(f"{case['id']}/{leaf_id}: harm must be 1 or 2")
            if not isinstance(leaf.get("allowPartial"), bool):
                validation.error(f"{case['id']}/{leaf_id}: allowPartial must be boolean")
            if isinstance(expectation, str):
                for pattern in UNEXPANDED_PATTERNS:
                    match = pattern.search(expectation)
                    if match:
                        validation.error(f"{case['id']}/{leaf_id}: unexpanded/template text: {match.group(0)!r}")
    missing_pages = sorted(set(range(1, int(case["pages"]) + 1)) - anchored_pages)
    if missing_pages:
        validation.error(f"{case['id']}: no scored region is anchored to page(s) {missing_pages}")
    return len(region_ids), leaf_count


def validate_spec(path: Path, case: dict[str, Any], validation: Validation) -> None:
    case_id = case["id"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        validation.error(f"{case_id}: cannot read spec {path}: {exc}")
        return
    if not text.startswith(f"# {case['title']}\n"):
        validation.error(f"{case_id}: spec H1 must exactly match manifest title")
    if "Source modality:" not in text:
        validation.error(f"{case_id}: spec must declare Source modality")
    for pattern in UNEXPANDED_PATTERNS:
        match = pattern.search(text)
        if match:
            validation.error(f"{case_id}: unexpanded/template text in spec: {match.group(0)!r}")


def render_pdf(pdf: Path, render_root: Path, case_id: str, validation: Validation) -> None:
    executable = shutil.which("pdftoppm")
    if not executable:
        validation.error("pdftoppm is required for --render")
        return
    if not SAFE_CASE_ID.fullmatch(case_id):
        validation.error(f"Unsafe case id for rendering: {case_id!r}")
        return
    render_root = render_root.resolve()
    out_dir = (render_root / case_id).resolve()
    try:
        out_dir.relative_to(render_root)
    except ValueError:
        validation.error(f"Render directory escapes render root for case {case_id!r}")
        return
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [executable, "-png", "-r", "144", str(pdf), str(out_dir / "page")],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        validation.error(f"{case_id}: pdftoppm failed: {result.stderr.strip()}")


def validate_benchmark(root: Path, render_root: Path | None) -> Validation:
    validation = Validation()
    root = root.resolve()
    manifest_path = root / "manifest.json"
    manifest = load_json(manifest_path, validation)
    if not isinstance(manifest, dict):
        return validation
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        validation.error("Manifest must contain non-empty cases[]")
        return validation
    if manifest.get("inputProtocol") != "native_pdf":
        validation.error("Manifest inputProtocol must be native_pdf")
    if manifest.get("caseCount") != len(cases):
        validation.error("Manifest caseCount does not equal len(cases)")

    case_ids: set[str] = set()
    total_pages = 0
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            validation.error("Manifest contains invalid case entry")
            continue
        case_id = case["id"]
        if not SAFE_CASE_ID.fullmatch(case_id):
            validation.error(f"Unsafe case id: {case_id!r}")
            continue
        if not isinstance(case.get("title"), str) or not case["title"].strip():
            validation.error(f"{case_id}: manifest title must be non-empty")
            continue
        if not isinstance(case.get("family"), str) or not case["family"].strip():
            validation.error(f"{case_id}: manifest family must be non-empty")
            continue
        if not isinstance(case.get("tags"), list) or not all(isinstance(tag, str) and tag for tag in case["tags"]):
            validation.error(f"{case_id}: manifest tags must be a list of non-empty strings")
            continue
        if case_id in case_ids:
            validation.error(f"Duplicate case id: {case_id}")
        case_ids.add(case_id)
        declared_pages = case.get("pages")
        if not isinstance(declared_pages, int) or declared_pages <= 0:
            validation.error(f"{case_id}: invalid page count {declared_pages!r}")
            continue
        total_pages += declared_pages

        pdf = resolve_artifact(case.get("pdf"), "pdf", case_id, validation)
        gold = resolve_artifact(case.get("gold"), "gold", case_id, validation)
        facts = resolve_artifact(case.get("facts"), "facts", case_id, validation)
        spec = resolve_artifact(case.get("spec"), "spec", case_id, validation)
        expected_names = {"pdf": "source.pdf", "gold": "gold.md", "facts": "facts.json", "spec": "spec.md"}
        for field, artifact in (("pdf", pdf), ("gold", gold), ("facts", facts), ("spec", spec)):
            expected = (root / "cases" / case_id / expected_names[field]).resolve()
            if artifact is not None and artifact != expected:
                validation.error(f"{case_id}: {field} must resolve to {expected}")
            if artifact is not None and not artifact.is_file():
                validation.error(f"{case_id}: missing or non-file {field} artifact {artifact}")

        actual_pages = 0
        extracted_words = 0
        layout = {"nativeTextPages": 0, "imagePages": 0, "fullPageRasterPages": 0}
        if pdf is not None and pdf.is_file():
            try:
                reader = PdfReader(str(pdf))
                actual_pages = len(reader.pages)
                if actual_pages != declared_pages:
                    validation.error(
                        f"{case_id}: PDF has {actual_pages} pages; manifest declares {declared_pages}"
                    )
                extracted = extract_pdf_text(reader)
                extracted_words = len(extracted.split())
                metadata = reader.metadata or {}
                if str(metadata.get("/Title", "")) != case["title"]:
                    validation.error(f"{case_id}: PDF title metadata does not match manifest")
                if "reportlab" in str(metadata.get("/Producer", "")).lower():
                    validation.error(f"{case_id}: PDF producer exposes the synthetic generation library")
                if str(metadata.get("/CreationDate", "")).startswith("D:2000") or str(metadata.get("/ModDate", "")).startswith("D:2000"):
                    validation.error(f"{case_id}: PDF metadata uses the invariant placeholder year 2000")
                source_text = extracted + "\n" + "\n".join(str(value) for value in metadata.values())
                normalized_source_text = re.sub(r"\s+", " ", source_text)
                if case_id.casefold() in normalized_source_text.casefold():
                    validation.error(f"{case_id}: exact benchmark case id leaks into the source PDF")
                for pattern in SOURCE_META_PATTERNS:
                    match = pattern.search(normalized_source_text)
                    if match:
                        validation.error(
                            f"{case_id}: extraction-facing source text detected: {match.group(0)!r}"
                        )
            except Exception as exc:  # noqa: BLE001 - validation must report corrupt PDFs
                validation.error(f"{case_id}: cannot parse PDF: {exc}")
            try:
                layout = inspect_pdf_layout(pdf, case_id, validation)
            except Exception as exc:  # noqa: BLE001 - layout audit must report malformed PDFs
                validation.error(f"{case_id}: cannot inspect PDF layout: {exc}")
            if render_root is not None:
                render_pdf(pdf, render_root, case_id, validation)

        if gold is not None and gold.is_file():
            validate_gold(gold, case, validation)
        if facts is not None and facts.is_file():
            region_count, leaf_count = validate_facts(facts, case, validation)
        else:
            region_count, leaf_count = 0, 0
        if spec is not None and spec.is_file():
            validate_spec(spec, case, validation)
        validation.cases.append(
            {
                "id": case_id,
                "pages": actual_pages,
                "extractedWords": extracted_words,
                **layout,
                "regions": region_count,
                "leaves": leaf_count,
            }
        )

    if manifest.get("pageCount") != total_pages:
        validation.error(
            f"Manifest pageCount {manifest.get('pageCount')!r} does not equal declared total {total_pages}"
        )
    return validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--render", type=Path, default=None, help="Render all pages to this directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validation = validate_benchmark(args.benchmark.resolve(), args.render.resolve() if args.render else None)
    report = {
        "ok": not validation.errors,
        "errors": validation.errors,
        "warnings": validation.warnings,
        "cases": validation.cases,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for case in validation.cases:
            print(
                f"{case['id']}: {case['pages']} pages, {case['extractedWords']} extracted words, "
                f"native text {case['nativeTextPages']}/{case['pages']}, images {case['imagePages']}/{case['pages']}, "
                f"full-page rasters {case['fullPageRasterPages']}, {case['regions']} regions, {case['leaves']} leaves"
            )
        for warning in validation.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        for error in validation.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("Benchmark validation passed." if not validation.errors else "Benchmark validation failed.")
    return 0 if not validation.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
