#!/usr/bin/env python3
"""Deterministically audit a Doc2MD corpus without calling model providers.

The audit joins four independently inspectable layers:

* the manifest's declared case and page inventory;
* physical PDF page contents (native glyphs and image XObjects);
* gold Markdown headings; and
* facts schema v3 regions, source anchors, and canonical claims.

It intentionally does not judge visual quality or semantic correctness.  Those
remain human-review tasks.  The JSON report is stable for unchanged inputs: it
contains no timestamps, random values, or environment-dependent ordering.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

import pdfplumber

try:
    from scripts.benchmark_cases.common import evidence_policy_violations
except ModuleNotFoundError:  # Direct ``python scripts/audit_benchmark.py`` execution.
    from benchmark_cases.common import evidence_policy_violations


AUDIT_SCHEMA_VERSION = 2
FULL_PAGE_IMAGE_AREA_RATIO = 0.90

SOURCE_LAYERS = (
    "native_text",
    "raster",
    "vector_geometry",
    "mixed",
    "native_layer_recovery",
)
REGION_KINDS = ("text", "table", "chart", "diagram", "form", "image", "structure", "mixed")
CAPABILITY_AXES = (
    "precise_recall",
    "table_reconstruction",
    "long_context_coherence",
    "reading_order",
    "form_state",
    "source_precedence",
    "chart_diagram_spatial",
    "image_description",
    "mixed_modality_fusion",
    "native_layer_recovery",
    "cross_page_join",
    "structure_reconstruction",
    "low_quality_scan",
    "summarization_coverage",
)
CLAIM_TYPES = (
    "scalar",
    "table_binding",
    "ordered_record",
    "directed_edge",
    "form_state",
    "source_precedence",
    "cross_page_join",
    "visual_description",
    "structure",
)
CLOSED_WORLD_SCOPES = (
    "region_claims",
    "table_rows",
    "form_options",
    "record_set",
    "edge_set",
    "structure_children",
)
PHYSICAL_MODALITIES = ("native-only", "full-page-raster", "mixed", "other")
VISUAL_KINDS = {"chart", "diagram", "image"}
VISUAL_AXES = {"chart_diagram_spatial", "image_description", "low_quality_scan"}

REGION_REQUIRED_FIELDS = {
    "id",
    "label",
    "sourceAnchors",
    "goldSection",
    "kind",
    "modality",
    "uniqueEvidence",
    "primaryAxis",
    "secondaryAxes",
    "textOnlyRecoverable",
    "budget",
    "leaves",
}
REGION_OPTIONAL_FIELDS = {"closedWorld"}
FACTS_FIELDS = {"schemaVersion", "id", "title", "family", "tags", "regions"}
LEAF_FIELDS = {"id", "canonicalClaimId", "claimType", "expectation", "harm", "evidencePolicy"}
ANCHOR_REQUIRED_FIELDS = {"page", "layer", "sectionPath"}
ANCHOR_OPTIONAL_FIELDS = {"bbox"}

H2_RE = re.compile(r"^ {0,3}##(?!#)\s+(.+?)\s*$")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _empty_counts(keys: Iterable[str]) -> dict[str, int]:
    return {key: 0 for key in keys}


def _sorted_counts(counter: Mapping[str, int], keys: Iterable[str]) -> dict[str, int]:
    result = {key: int(counter.get(key, 0)) for key in keys}
    for key in sorted(set(counter) - set(result)):
        result[key] = int(counter[key])
    return result


def _share(numerator: int | float, denominator: int | float) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _budget_shares(counts: Mapping[str, int], keys: Iterable[str], total: int) -> dict[str, float]:
    return {key: _share(int(counts.get(key, 0)), total) for key in keys}


def _equal_case_budget_shares(
    cases: Sequence[Mapping[str, Any]],
    field: str,
    keys: Iterable[str],
) -> dict[str, float]:
    """Return each slice's effective share under the official equal-case score.

    A region contributes ``region budget / its case budget`` inside its case,
    and each case contributes exactly ``1 / case count`` to the suite. This is
    deliberately different from pooling all region budgets across documents.
    """
    key_list = list(keys)
    if not cases:
        return {key: 0.0 for key in key_list}
    totals = {key: 0.0 for key in key_list}
    for case in cases:
        case_budget = int(case.get("budget", 0))
        counts = case.get(field, {})
        if not isinstance(counts, Mapping) or case_budget <= 0:
            continue
        for key in key_list:
            totals[key] += int(counts.get(key, 0)) / case_budget
    return {key: round(totals[key] / len(cases), 6) for key in key_list}


def _budget_accounting(cases: Sequence[Mapping[str, Any]], suite: Mapping[str, Any]) -> dict[str, Any]:
    total = int(suite["budget"])
    raw_text_only = int(suite["textOnlyRecoverable"]["budget"])
    effective_text_only = (
        sum(
            int(case["textOnlyRecoverable"]["budget"]) / int(case["budget"])
            for case in cases
            if int(case["budget"]) > 0
        )
        / len(cases)
        if cases
        else 0.0
    )
    return {
        "rawPooled": {
            "totalBudget": total,
            "budgetByModality": dict(suite["budgetByModality"]),
            "shareByModality": _budget_shares(suite["budgetByModality"], SOURCE_LAYERS, total),
            "budgetByKind": dict(suite["budgetByKind"]),
            "shareByKind": _budget_shares(suite["budgetByKind"], REGION_KINDS, total),
            "budgetByPrimaryAxis": dict(suite["budgetByPrimaryAxis"]),
            "shareByPrimaryAxis": _budget_shares(suite["budgetByPrimaryAxis"], CAPABILITY_AXES, total),
            "textOnlyRecoverableBudget": raw_text_only,
            "textOnlyRecoverableShare": _share(raw_text_only, total),
        },
        "equalCaseEffectiveShares": {
            "caseWeight": _share(1, len(cases)),
            "byModality": _equal_case_budget_shares(cases, "budgetByModality", SOURCE_LAYERS),
            "byKind": _equal_case_budget_shares(cases, "budgetByKind", REGION_KINDS),
            "byPrimaryAxis": _equal_case_budget_shares(cases, "budgetByPrimaryAxis", CAPABILITY_AXES),
            "textOnlyRecoverable": round(effective_text_only, 6),
        },
    }


def _finding(code: str, message: str, **context: Any) -> dict[str, Any]:
    finding: dict[str, Any] = {"code": code, "message": message}
    for key in sorted(context):
        value = context[key]
        if value is not None:
            finding[key] = value
    return finding


class AuditState:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def error(self, case: MutableMapping[str, Any] | None, code: str, message: str, **context: Any) -> None:
        finding = _finding(code, message, **context)
        self.errors.append(finding)
        if case is not None:
            case["errors"].append(finding)

    def warning(self, case: MutableMapping[str, Any] | None, code: str, message: str, **context: Any) -> None:
        finding = _finding(code, message, **context)
        self.warnings.append(finding)
        if case is not None:
            case["warnings"].append(finding)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_artifact(manifest_path: Path, value: Any) -> Path | None:
    if not _is_nonempty_string(value):
        return None
    raw = Path(value)
    if raw.is_absolute():
        return raw.resolve()

    # Fixture manifests usually use paths relative to their own directory.
    # The official manifest lives in benchmark/ but uses repository-relative
    # paths beginning with benchmark/.  Prefer the local interpretation when it
    # exists, then the repository-parent interpretation used by that manifest.
    local = (manifest_path.parent / raw).resolve()
    parent_relative = (manifest_path.parent.parent / raw).resolve()
    if local.exists() or not parent_relative.exists():
        return local
    return parent_relative


def _artifact_record(declared: Any, resolved: Path | None) -> dict[str, Any]:
    exists = resolved is not None and resolved.is_file()
    return {
        "declaredPath": declared if isinstance(declared, str) else None,
        "resolvedPath": str(resolved) if resolved is not None else None,
        "exists": exists,
        "sha256": _sha256(resolved) if exists else None,
    }


def _normalized_heading(value: str) -> str:
    value = value.strip()
    # Markdown permits optional closing hashes.  Gold-section names are stored
    # without them, so discard only a syntactically separated closing run.
    return re.sub(r"\s+#+\s*$", "", value).strip()


def _gold_inventory(path: Path, title: str, case: MutableMapping[str, Any], state: AuditState) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        state.error(case, "GOLD_READ_ERROR", f"Cannot read gold Markdown: {exc}", caseId=case["id"])
        return {"titleMatchesManifest": False, "h2Headings": [], "duplicateH2Headings": []}

    first_nonempty = next((line.strip() for line in text.splitlines() if line.strip()), "")
    title_matches = first_nonempty == f"# {title}"
    if not title_matches:
        state.error(
            case,
            "GOLD_TITLE_MISMATCH",
            "The first non-empty gold line must be an H1 matching the manifest title.",
            caseId=case["id"],
        )

    headings = [_normalized_heading(match.group(1)) for line in text.splitlines() if (match := H2_RE.match(line))]
    duplicate_headings = sorted(key for key, count in Counter(headings).items() if count > 1)
    for heading in duplicate_headings:
        state.error(
            case,
            "DUPLICATE_GOLD_SECTION",
            f"Gold H2 section {heading!r} is duplicated and therefore ambiguous.",
            caseId=case["id"],
            goldSection=heading,
        )
    return {
        "titleMatchesManifest": title_matches,
        "h2Headings": headings,
        "duplicateH2Headings": duplicate_headings,
    }


def _page_vector_object_count(page: Any) -> int:
    return sum(len(getattr(page, name, []) or []) for name in ("lines", "rects", "curves"))


def _inspect_pdf(path: Path, case: MutableMapping[str, Any], state: AuditState) -> tuple[list[dict[str, Any]], int]:
    pages: list[dict[str, Any]] = []
    extracted_words = 0
    try:
        with pdfplumber.open(path) as document:
            for page_number, page in enumerate(document.pages, start=1):
                nonblank_chars = [char for char in page.chars if str(char.get("text", "")).strip()]
                images = list(page.images)
                page_area = float(page.width) * float(page.height)
                image_area_ratios: list[float] = []
                for image in images:
                    width = max(0.0, float(image.get("x1", 0)) - float(image.get("x0", 0)))
                    height = max(0.0, float(image.get("y1", 0)) - float(image.get("y0", 0)))
                    image_area_ratios.append((width * height / page_area) if page_area else 0.0)
                maximum_image_area_ratio = max(image_area_ratios, default=0.0)
                has_native_text = bool(nonblank_chars)
                has_images = bool(images)
                has_full_page_image = maximum_image_area_ratio >= FULL_PAGE_IMAGE_AREA_RATIO

                if has_native_text and has_images:
                    modality = "mixed"
                elif has_native_text:
                    modality = "native-only"
                elif has_full_page_image:
                    modality = "full-page-raster"
                else:
                    modality = "other"
                    state.warning(
                        case,
                        "UNCLASSIFIED_PHYSICAL_PAGE",
                        "Page is neither native-text, full-page-raster, nor mixed by observable glyph/image rules.",
                        caseId=case["id"],
                        page=page_number,
                    )

                extracted = page.extract_text() or ""
                words = len(extracted.split())
                extracted_words += words
                pages.append(
                    {
                        "page": page_number,
                        "physicalModality": modality,
                        "nativeCharacterCount": len(nonblank_chars),
                        "imageCount": len(images),
                        "fullPageImage": has_full_page_image,
                        "maximumImageAreaShare": round(maximum_image_area_ratio, 6),
                        "vectorObjectCount": _page_vector_object_count(page),
                        "extractedWords": words,
                    }
                )
    except Exception as exc:  # noqa: BLE001 - corrupt PDFs must become report findings
        state.error(case, "PDF_READ_ERROR", f"Cannot inspect source PDF: {exc}", caseId=case["id"])
    return pages, extracted_words


def _validate_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_nonempty_string(item) for item in value)


def _validate_term_groups(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_validate_string_list(group) for group in value)


def _validate_policy(policy: Any) -> tuple[bool, str | None]:
    if not isinstance(policy, dict):
        return False, None
    policy_type = policy.get("type")
    if policy_type == "lexical":
        return set(policy) == {"type", "allOf"} and _validate_term_groups(policy.get("allOf")), policy_type
    if policy_type == "table_binding":
        valid = set(policy) == {"type", "row", "column", "value"} and all(
            _validate_string_list(policy.get(field)) for field in ("row", "column", "value")
        )
        return valid, policy_type
    if policy_type == "form_state":
        valid = (
            set(policy) == {"type", "label", "state"}
            and _validate_string_list(policy.get("label"))
            and policy.get("state") in {"checked", "unchecked", "disabled", "crossed"}
        )
        return valid, policy_type
    if policy_type == "directed_edge":
        fields = set(policy)
        valid = (
            {"type", "source", "destination"} <= fields <= {"type", "source", "destination", "relation"}
            and _validate_string_list(policy.get("source"))
            and _validate_string_list(policy.get("destination"))
            and ("relation" not in policy or _validate_string_list(policy.get("relation")))
        )
        return valid, policy_type
    if policy_type == "ordered_tokens":
        return set(policy) == {"type", "tokens"} and _validate_term_groups(policy.get("tokens")), policy_type
    if policy_type == "qualitative":
        valid = set(policy) == {"type", "requiredTerms"} and _validate_term_groups(policy.get("requiredTerms"))
        return valid, policy_type
    return False, policy_type if isinstance(policy_type, str) else None


def _valid_bbox(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) and 0 <= item <= 1 for item in value)
        and value[0] < value[2]
        and value[1] < value[3]
    )


def _anchor_contradiction(layer: str, page: Mapping[str, Any]) -> str | None:
    native = int(page["nativeCharacterCount"]) > 0
    raster = int(page["imageCount"]) > 0
    vector = int(page["vectorObjectCount"]) > 0
    if layer in {"native_text", "native_layer_recovery"} and not native:
        return "the page has no observable native text glyphs"
    if layer == "raster" and not raster:
        return "the page has no observable image XObject"
    if layer == "mixed" and not (native and raster):
        return "the page does not contain both native glyphs and an image XObject"
    if layer == "vector_geometry" and not vector:
        return "the page has no observable line, rectangle, or curve object"
    return None


def _validate_facts(
    facts: Any,
    manifest_case: Mapping[str, Any],
    gold: Mapping[str, Any],
    physical_pages: Sequence[Mapping[str, Any]],
    case: MutableMapping[str, Any],
    state: AuditState,
) -> dict[str, Any]:
    case_id = case["id"]
    page_lookup = {int(page["page"]): page for page in physical_pages}
    declared_pages = manifest_case.get("pages") if _is_int(manifest_case.get("pages")) else len(physical_pages)
    metrics: dict[str, Any] = {
        "regionCount": 0,
        "leafCount": 0,
        "budget": 0,
        "budgetByModality": _empty_counts(SOURCE_LAYERS),
        "budgetByKind": _empty_counts(REGION_KINDS),
        "budgetByPrimaryAxis": _empty_counts(CAPABILITY_AXES),
        "budgetAccounting": {
            "rawPooled": {
                "totalBudget": 0,
                "budgetByModality": _empty_counts(SOURCE_LAYERS),
                "shareByModality": {key: 0.0 for key in SOURCE_LAYERS},
                "budgetByKind": _empty_counts(REGION_KINDS),
                "shareByKind": {key: 0.0 for key in REGION_KINDS},
                "budgetByPrimaryAxis": _empty_counts(CAPABILITY_AXES),
                "shareByPrimaryAxis": {key: 0.0 for key in CAPABILITY_AXES},
                "textOnlyRecoverableBudget": 0,
                "textOnlyRecoverableShare": 0.0,
            },
            "equalCaseEffectiveShares": {
                "caseWeight": 0.0,
                "byModality": {key: 0.0 for key in SOURCE_LAYERS},
                "byKind": {key: 0.0 for key in REGION_KINDS},
                "byPrimaryAxis": {key: 0.0 for key in CAPABILITY_AXES},
                "textOnlyRecoverable": 0.0,
            },
        },
        "textOnlyRecoverableBudget": 0,
        "anchoredPages": set(),
        "sourceAnchorCount": 0,
        "sourceAnchorContradictionCount": 0,
        "goldSectionsReferenced": set(),
        "missingGoldSections": set(),
        "duplicateCanonicalClaims": set(),
        "evidencePolicyCompletenessViolationCount": 0,
        "schemaV3Valid": True,
        "metadataMatchesManifest": True,
    }

    facts_error_start = len(case["errors"])

    def facts_error(code: str, message: str, **context: Any) -> None:
        state.error(case, code, message, caseId=case_id, **context)

    if not isinstance(facts, dict):
        facts_error("FACTS_ROOT_INVALID", "Facts JSON root must be an object.")
        metrics["schemaV3Valid"] = False
        metrics["metadataMatchesManifest"] = False
        return metrics
    if set(facts) != FACTS_FIELDS:
        facts_error(
            "FACTS_ROOT_SCHEMA_FIELDS",
            "Facts root fields do not match the audited schema v3 corpus contract.",
            missingFields=sorted(FACTS_FIELDS - set(facts)),
            unknownFields=sorted(set(facts) - FACTS_FIELDS),
        )
    if facts.get("schemaVersion") != 3:
        facts_error("FACTS_SCHEMA_VERSION", "Facts schemaVersion must be 3.", actual=facts.get("schemaVersion"))
    for field in ("id", "title", "family", "tags"):
        if facts.get(field) != manifest_case.get(field):
            facts_error(
                "FACTS_MANIFEST_MISMATCH",
                f"Facts {field} does not match the manifest.",
                field=field,
            )
            metrics["metadataMatchesManifest"] = False

    regions = facts.get("regions")
    if not isinstance(regions, list) or not regions:
        facts_error("FACTS_REGIONS_INVALID", "Facts regions must be a non-empty array.")
        metrics["schemaV3Valid"] = False
        return metrics

    region_ids: set[str] = set()
    leaf_ids: set[str] = set()
    canonical_claims: dict[str, str] = {}
    normalized_expectations: dict[str, str] = {}
    gold_headings = set(gold.get("h2Headings", []))

    for region_index, region in enumerate(regions):
        if not isinstance(region, dict):
            facts_error("REGION_INVALID", "Region must be an object.", regionIndex=region_index)
            continue
        metrics["regionCount"] += 1
        region_id = region.get("id") if _is_nonempty_string(region.get("id")) else f"<region-{region_index}>"
        actual_fields = set(region)
        missing_fields = sorted(REGION_REQUIRED_FIELDS - actual_fields)
        unknown_fields = sorted(actual_fields - REGION_REQUIRED_FIELDS - REGION_OPTIONAL_FIELDS)
        if missing_fields or unknown_fields:
            facts_error(
                "REGION_SCHEMA_FIELDS",
                "Region fields do not match facts schema v3.",
                regionId=region_id,
                missingFields=missing_fields,
                unknownFields=unknown_fields,
            )
        if not _is_nonempty_string(region.get("id")):
            facts_error("REGION_ID_INVALID", "Region id must be a non-empty string.", regionIndex=region_index)
        elif region_id in region_ids:
            facts_error("DUPLICATE_REGION_ID", f"Duplicate region id {region_id!r}.", regionId=region_id)
        region_ids.add(region_id)
        if not _is_nonempty_string(region.get("label")):
            facts_error("REGION_LABEL_INVALID", "Region label must be a non-empty string.", regionId=region_id)

        budget = region.get("budget")
        valid_budget = _is_int(budget) and budget in {1, 2, 3, 4}
        if not valid_budget:
            facts_error("REGION_BUDGET_INVALID", "Region budget must be an integer from 1 through 4.", regionId=region_id)
            budget = 0
        metrics["budget"] += budget

        modality = region.get("modality")
        kind = region.get("kind")
        primary_axis = region.get("primaryAxis")
        if modality not in SOURCE_LAYERS:
            facts_error("REGION_MODALITY_INVALID", f"Unsupported region modality {modality!r}.", regionId=region_id)
        elif valid_budget:
            metrics["budgetByModality"][modality] += budget
        if kind not in REGION_KINDS:
            facts_error("REGION_KIND_INVALID", f"Unsupported region kind {kind!r}.", regionId=region_id)
        elif valid_budget:
            metrics["budgetByKind"][kind] += budget
        if primary_axis not in CAPABILITY_AXES:
            facts_error("REGION_PRIMARY_AXIS_INVALID", f"Unsupported primary capability axis {primary_axis!r}.", regionId=region_id)
        elif valid_budget:
            metrics["budgetByPrimaryAxis"][primary_axis] += budget
        secondary_axes = region.get("secondaryAxes")
        if (
            not isinstance(secondary_axes, list)
            or any(axis not in CAPABILITY_AXES for axis in secondary_axes)
            or len(secondary_axes) != len(set(secondary_axes))
            or primary_axis in secondary_axes
        ):
            facts_error("REGION_SECONDARY_AXES_INVALID", "Region secondaryAxes must be unique supported axes excluding primaryAxis.", regionId=region_id)
        if not isinstance(region.get("uniqueEvidence"), bool):
            facts_error("REGION_UNIQUE_EVIDENCE_INVALID", "Region uniqueEvidence must be boolean.", regionId=region_id)

        text_only = region.get("textOnlyRecoverable")
        if not isinstance(text_only, bool):
            facts_error("REGION_TEXT_ONLY_INVALID", "Region textOnlyRecoverable must be boolean.", regionId=region_id)
        elif text_only:
            if valid_budget:
                metrics["textOnlyRecoverableBudget"] += budget
            axes = {primary_axis} | (set(secondary_axes) if isinstance(secondary_axes, list) else set())
            visual = kind in VISUAL_KINDS or bool(axes & VISUAL_AXES)
            raw_anchors = region.get("sourceAnchors")
            anchor_layers = {
                anchor.get("layer")
                for anchor in raw_anchors
                if isinstance(anchor, dict)
            } if isinstance(raw_anchors, list) else set()
            raster = modality == "raster" or bool(anchor_layers & {"raster", "mixed"})
            if visual or raster:
                facts_error(
                    "TEXT_ONLY_VISUAL_OR_RASTER",
                    "A visual or raster-dependent region cannot be marked textOnlyRecoverable.",
                    regionId=region_id,
                )

        gold_section = region.get("goldSection")
        if not _is_nonempty_string(gold_section):
            facts_error("REGION_GOLD_SECTION_INVALID", "Region goldSection must be a non-empty string.", regionId=region_id)
        else:
            metrics["goldSectionsReferenced"].add(gold_section)
            if gold_section not in gold_headings:
                metrics["missingGoldSections"].add(gold_section)
                facts_error(
                    "GOLD_SECTION_NOT_FOUND",
                    f"Region goldSection {gold_section!r} has no exact H2 in gold Markdown.",
                    regionId=region_id,
                    goldSection=gold_section,
                )

        closed_world = region.get("closedWorld")
        if closed_world is not None:
            valid_closed_world = (
                isinstance(closed_world, dict)
                and set(closed_world) == {"scope", "keys"}
                and closed_world.get("scope") in CLOSED_WORLD_SCOPES
                and _validate_string_list(closed_world.get("keys"))
            )
            if not valid_closed_world:
                facts_error("CLOSED_WORLD_INVALID", "closedWorld must match the facts schema v3 contract.", regionId=region_id)
            elif len({key.strip().casefold() for key in closed_world["keys"]}) != len(closed_world["keys"]):
                facts_error("CLOSED_WORLD_DUPLICATE_KEYS", "closedWorld keys must be case-insensitively unique.", regionId=region_id)

        anchors = region.get("sourceAnchors")
        if not isinstance(anchors, list) or not anchors:
            facts_error("SOURCE_ANCHORS_INVALID", "Region sourceAnchors must be a non-empty array.", regionId=region_id)
            anchors = []
        for anchor_index, anchor in enumerate(anchors):
            metrics["sourceAnchorCount"] += 1
            if not isinstance(anchor, dict):
                facts_error("SOURCE_ANCHOR_INVALID", "Source anchor must be an object.", regionId=region_id, anchorIndex=anchor_index)
                continue
            actual_anchor_fields = set(anchor)
            if not ANCHOR_REQUIRED_FIELDS <= actual_anchor_fields <= ANCHOR_REQUIRED_FIELDS | ANCHOR_OPTIONAL_FIELDS:
                facts_error(
                    "SOURCE_ANCHOR_SCHEMA_FIELDS",
                    "Source anchor fields do not match facts schema v3.",
                    regionId=region_id,
                    anchorIndex=anchor_index,
                    missingFields=sorted(ANCHOR_REQUIRED_FIELDS - actual_anchor_fields),
                    unknownFields=sorted(actual_anchor_fields - ANCHOR_REQUIRED_FIELDS - ANCHOR_OPTIONAL_FIELDS),
                )
            page_number = anchor.get("page")
            if not _is_int(page_number) or not 1 <= page_number <= declared_pages:
                facts_error(
                    "SOURCE_ANCHOR_PAGE_INVALID",
                    f"Source anchor page {page_number!r} is outside the declared document.",
                    regionId=region_id,
                    anchorIndex=anchor_index,
                )
            else:
                metrics["anchoredPages"].add(page_number)
                if physical_pages and page_number not in page_lookup:
                    facts_error(
                        "SOURCE_ANCHOR_PHYSICAL_PAGE_MISSING",
                        "Source anchor refers to a declared page absent from the physical PDF.",
                        regionId=region_id,
                        anchorIndex=anchor_index,
                        page=page_number,
                    )
            layer = anchor.get("layer")
            if layer not in SOURCE_LAYERS:
                facts_error("SOURCE_ANCHOR_LAYER_INVALID", f"Unsupported source anchor layer {layer!r}.", regionId=region_id, anchorIndex=anchor_index)
            if not _validate_string_list(anchor.get("sectionPath")):
                facts_error("SOURCE_ANCHOR_SECTION_PATH_INVALID", "Source anchor sectionPath must contain non-empty strings.", regionId=region_id, anchorIndex=anchor_index)
            if "bbox" in anchor and not _valid_bbox(anchor.get("bbox")):
                facts_error("SOURCE_ANCHOR_BBOX_INVALID", "Source anchor bbox must be normalized [x0,y0,x1,y1].", regionId=region_id, anchorIndex=anchor_index)

            physical_page = page_lookup.get(page_number) if _is_int(page_number) else None
            if physical_page is not None and layer in SOURCE_LAYERS:
                contradiction = _anchor_contradiction(layer, physical_page)
                if contradiction is not None:
                    metrics["sourceAnchorContradictionCount"] += 1
                    facts_error(
                        "SOURCE_ANCHOR_PHYSICAL_CONTRADICTION",
                        f"Anchor claims {layer!r}, but {contradiction}.",
                        regionId=region_id,
                        anchorIndex=anchor_index,
                        page=page_number,
                        layer=layer,
                    )

        leaves = region.get("leaves")
        if not isinstance(leaves, list) or not leaves:
            facts_error("REGION_LEAVES_INVALID", "Region leaves must be a non-empty array.", regionId=region_id)
            continue
        for leaf_index, leaf in enumerate(leaves):
            if not isinstance(leaf, dict):
                facts_error("LEAF_INVALID", "Leaf must be an object.", regionId=region_id, leafIndex=leaf_index)
                continue
            metrics["leafCount"] += 1
            leaf_id = leaf.get("id") if _is_nonempty_string(leaf.get("id")) else f"<leaf-{leaf_index}>"
            if set(leaf) != LEAF_FIELDS:
                facts_error(
                    "LEAF_SCHEMA_FIELDS",
                    "Leaf fields do not match facts schema v3.",
                    regionId=region_id,
                    leafId=leaf_id,
                    missingFields=sorted(LEAF_FIELDS - set(leaf)),
                    unknownFields=sorted(set(leaf) - LEAF_FIELDS),
                )
            if not _is_nonempty_string(leaf.get("id")):
                facts_error("LEAF_ID_INVALID", "Leaf id must be a non-empty string.", regionId=region_id, leafIndex=leaf_index)
            elif leaf_id in leaf_ids:
                facts_error("DUPLICATE_LEAF_ID", f"Duplicate leaf id {leaf_id!r}.", regionId=region_id, leafId=leaf_id)
            leaf_ids.add(leaf_id)

            canonical_id = leaf.get("canonicalClaimId")
            if not _is_nonempty_string(canonical_id):
                facts_error("CANONICAL_CLAIM_ID_INVALID", "canonicalClaimId must be a non-empty string.", regionId=region_id, leafId=leaf_id)
            elif canonical_id in canonical_claims:
                metrics["duplicateCanonicalClaims"].add(canonical_id)
                facts_error(
                    "DUPLICATE_CANONICAL_CLAIM",
                    f"canonicalClaimId {canonical_id!r} is used by more than one leaf.",
                    regionId=region_id,
                    leafId=leaf_id,
                    firstLeafId=canonical_claims[canonical_id],
                    canonicalClaimId=canonical_id,
                )
            else:
                canonical_claims[canonical_id] = leaf_id

            expectation = leaf.get("expectation")
            if not _is_nonempty_string(expectation):
                facts_error("LEAF_EXPECTATION_INVALID", "Leaf expectation must be a non-empty string.", regionId=region_id, leafId=leaf_id)
            else:
                normalized = re.sub(r"\s+", " ", expectation).strip().casefold()
                if normalized in normalized_expectations and normalized_expectations[normalized] != canonical_id:
                    facts_error(
                        "DUPLICATE_CANONICAL_EXPECTATION",
                        "Two different canonicalClaimIds have the same normalized expectation.",
                        regionId=region_id,
                        leafId=leaf_id,
                        firstCanonicalClaimId=normalized_expectations[normalized],
                        canonicalClaimId=canonical_id,
                    )
                else:
                    normalized_expectations[normalized] = canonical_id
            if leaf.get("harm") not in {1, 2} or not _is_int(leaf.get("harm")):
                facts_error("LEAF_HARM_INVALID", "Leaf harm must be integer 1 or 2.", regionId=region_id, leafId=leaf_id)
            claim_type = leaf.get("claimType")
            if claim_type not in CLAIM_TYPES:
                facts_error("LEAF_CLAIM_TYPE_INVALID", f"Unsupported claimType {claim_type!r}.", regionId=region_id, leafId=leaf_id)
            valid_policy, policy_type = _validate_policy(leaf.get("evidencePolicy"))
            if not valid_policy:
                facts_error("LEAF_EVIDENCE_POLICY_INVALID", "evidencePolicy does not match a facts schema v3 policy.", regionId=region_id, leafId=leaf_id)
            required_policy = {
                "table_binding": "table_binding",
                "ordered_record": "ordered_tokens",
                "directed_edge": "directed_edge",
                "form_state": "form_state",
                "source_precedence": "ordered_tokens",
                "visual_description": "qualitative",
            }.get(claim_type)
            if valid_policy and required_policy is not None and policy_type != required_policy:
                facts_error(
                    "LEAF_POLICY_CLAIM_MISMATCH",
                    f"claimType {claim_type!r} requires {required_policy!r} evidence.",
                    regionId=region_id,
                    leafId=leaf_id,
                )
            if valid_policy and _is_nonempty_string(expectation):
                completeness_violations = evidence_policy_violations(expectation, leaf["evidencePolicy"])
                metrics["evidencePolicyCompletenessViolationCount"] += len(completeness_violations)
                for violation in completeness_violations:
                    facts_error(
                        "LEAF_EVIDENCE_POLICY_SIGNAL_MISSING",
                        "evidencePolicy does not guarantee a high-signal literal asserted by the expectation.",
                        regionId=region_id,
                        leafId=leaf_id,
                        signalKind=violation.signal.kind,
                        signal=violation.signal.value,
                        reason=violation.reason,
                    )

    missing_pages = sorted(set(range(1, declared_pages + 1)) - metrics["anchoredPages"])
    for page_number in missing_pages:
        facts_error(
            "UNANCHORED_PAGE",
            "No scored region is anchored to this declared page.",
            page=page_number,
        )

    # Keep schema validity distinct from cross-artifact traceability.  Both are
    # release-blocking errors, but a physically false anchor does not make an
    # otherwise well-shaped JSON object cease to be schema v3.
    traceability_only_codes = {
        "FACTS_MANIFEST_MISMATCH",
        "GOLD_SECTION_NOT_FOUND",
        "SOURCE_ANCHOR_PHYSICAL_CONTRADICTION",
        "SOURCE_ANCHOR_PHYSICAL_PAGE_MISSING",
        "TEXT_ONLY_VISUAL_OR_RASTER",
        "DUPLICATE_CANONICAL_EXPECTATION",
        "UNANCHORED_PAGE",
    }
    facts_findings = case["errors"][facts_error_start:]
    metrics["schemaV3Valid"] = not any(
        finding["code"] not in traceability_only_codes for finding in facts_findings
    )
    return metrics


def _new_case(case_id: str, title: str) -> dict[str, Any]:
    return {
        "id": case_id,
        "title": title,
        "ok": False,
        "artifacts": {},
        "pages": [],
        "physicalPageModalityCounts": _empty_counts(PHYSICAL_MODALITIES),
        "extractedWords": 0,
        "regionCount": 0,
        "leafCount": 0,
        "budget": 0,
        "budgetByModality": _empty_counts(SOURCE_LAYERS),
        "budgetByKind": _empty_counts(REGION_KINDS),
        "budgetByPrimaryAxis": _empty_counts(CAPABILITY_AXES),
        "textOnlyRecoverable": {"budget": 0, "totalBudget": 0, "budgetShare": 0.0},
        "anchoredPageCoverage": {"anchoredPages": 0, "declaredPages": 0, "share": 0.0, "missingPages": []},
        "traceability": {
            "factsSchemaV3Valid": False,
            "factsMetadataMatchesManifest": False,
            "goldTitleMatchesManifest": False,
            "goldSectionsReferenced": 0,
            "missingGoldSections": [],
            "unreferencedGoldSections": [],
            "sourceAnchorCount": 0,
            "sourceAnchorContradictionCount": 0,
            "duplicateCanonicalClaims": [],
            "evidencePolicyCompletenessViolationCount": 0,
        },
        "errors": [],
        "warnings": [],
    }


def audit_manifest(manifest_path: Path) -> dict[str, Any]:
    """Return a deterministic, JSON-serializable audit report."""

    manifest_path = manifest_path.expanduser().resolve()
    state = AuditState()
    report: dict[str, Any] = {
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "manifest": {
            "path": str(manifest_path),
            "exists": manifest_path.is_file(),
            "sha256": _sha256(manifest_path) if manifest_path.is_file() else None,
        },
        "ok": False,
        "suite": {},
        "cases": [],
        "errors": state.errors,
        "warnings": state.warnings,
    }
    if not manifest_path.is_file():
        state.error(None, "MANIFEST_MISSING", "Manifest file does not exist.", path=str(manifest_path))
        report["suite"] = _empty_suite()
        return report
    try:
        manifest = _load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        state.error(None, "MANIFEST_READ_ERROR", f"Cannot load manifest JSON: {exc}", path=str(manifest_path))
        report["suite"] = _empty_suite()
        return report
    if not isinstance(manifest, dict):
        state.error(None, "MANIFEST_ROOT_INVALID", "Manifest JSON root must be an object.")
        report["suite"] = _empty_suite()
        return report
    manifest_cases = manifest.get("cases")
    if not isinstance(manifest_cases, list) or not manifest_cases:
        state.error(None, "MANIFEST_CASES_INVALID", "Manifest cases must be a non-empty array.")
        report["suite"] = _empty_suite()
        return report
    if manifest.get("caseCount") != len(manifest_cases):
        state.error(
            None,
            "MANIFEST_CASE_COUNT_MISMATCH",
            "Manifest caseCount does not equal the number of cases.",
            actual=len(manifest_cases),
            declared=manifest.get("caseCount"),
        )

    seen_case_ids: set[str] = set()
    declared_page_total = 0
    for case_index, manifest_case in enumerate(manifest_cases):
        if not isinstance(manifest_case, dict):
            case = _new_case(f"<case-{case_index}>", "")
            report["cases"].append(case)
            state.error(case, "MANIFEST_CASE_INVALID", "Manifest case must be an object.", caseIndex=case_index)
            continue
        case_id = manifest_case.get("id") if _is_nonempty_string(manifest_case.get("id")) else f"<case-{case_index}>"
        title = manifest_case.get("title") if _is_nonempty_string(manifest_case.get("title")) else ""
        case = _new_case(case_id, title)
        report["cases"].append(case)
        if not _is_nonempty_string(manifest_case.get("id")):
            state.error(case, "MANIFEST_CASE_ID_INVALID", "Case id must be a non-empty string.", caseIndex=case_index)
        elif case_id in seen_case_ids:
            state.error(case, "DUPLICATE_CASE_ID", f"Duplicate case id {case_id!r}.", caseId=case_id)
        seen_case_ids.add(case_id)
        for field in ("title", "family"):
            if not _is_nonempty_string(manifest_case.get(field)):
                state.error(case, "MANIFEST_CASE_FIELD_INVALID", f"Case {field} must be a non-empty string.", caseId=case_id, field=field)
        if not isinstance(manifest_case.get("tags"), list) or not all(_is_nonempty_string(tag) for tag in manifest_case.get("tags", [])):
            state.error(case, "MANIFEST_CASE_TAGS_INVALID", "Case tags must be an array of non-empty strings.", caseId=case_id)
        declared_pages = manifest_case.get("pages")
        if not _is_int(declared_pages) or declared_pages < 1:
            state.error(case, "MANIFEST_CASE_PAGES_INVALID", "Case pages must be a positive integer.", caseId=case_id)
            declared_pages = 0
        declared_page_total += declared_pages

        artifacts: dict[str, Path | None] = {}
        for artifact_name in ("pdf", "gold", "facts"):
            declared = manifest_case.get(artifact_name)
            resolved = _resolve_artifact(manifest_path, declared)
            artifacts[artifact_name] = resolved
            case["artifacts"][artifact_name] = _artifact_record(declared, resolved)
            if resolved is None or not resolved.is_file():
                state.error(
                    case,
                    "ARTIFACT_MISSING",
                    f"Manifest {artifact_name} artifact is missing or invalid.",
                    caseId=case_id,
                    artifact=artifact_name,
                    path=str(resolved) if resolved is not None else None,
                )

        physical_pages: list[dict[str, Any]] = []
        if artifacts["pdf"] is not None and artifacts["pdf"].is_file():
            physical_pages, extracted_words = _inspect_pdf(artifacts["pdf"], case, state)
            case["pages"] = physical_pages
            case["extractedWords"] = extracted_words
            case["physicalPageModalityCounts"] = _sorted_counts(
                Counter(page["physicalModality"] for page in physical_pages), PHYSICAL_MODALITIES
            )
            if len(physical_pages) != declared_pages:
                state.error(
                    case,
                    "PDF_PAGE_COUNT_MISMATCH",
                    "Physical PDF page count does not match the manifest.",
                    caseId=case_id,
                    actual=len(physical_pages),
                    declared=declared_pages,
                )

        gold = {"titleMatchesManifest": False, "h2Headings": [], "duplicateH2Headings": []}
        if artifacts["gold"] is not None and artifacts["gold"].is_file():
            gold = _gold_inventory(artifacts["gold"], title, case, state)

        facts_metrics: dict[str, Any] | None = None
        if artifacts["facts"] is not None and artifacts["facts"].is_file():
            try:
                facts = _load_json(artifacts["facts"])
            except (OSError, json.JSONDecodeError) as exc:
                state.error(case, "FACTS_READ_ERROR", f"Cannot load facts JSON: {exc}", caseId=case_id)
            else:
                facts_metrics = _validate_facts(facts, manifest_case, gold, physical_pages, case, state)

        if facts_metrics is not None:
            for key in (
                "regionCount",
                "leafCount",
                "budget",
                "budgetByModality",
                "budgetByKind",
                "budgetByPrimaryAxis",
            ):
                case[key] = facts_metrics[key]
            text_only_budget = facts_metrics["textOnlyRecoverableBudget"]
            case["textOnlyRecoverable"] = {
                "budget": text_only_budget,
                "totalBudget": facts_metrics["budget"],
                "budgetShare": _share(text_only_budget, facts_metrics["budget"]),
            }
            anchored_pages = facts_metrics["anchoredPages"]
            missing_pages = sorted(set(range(1, declared_pages + 1)) - anchored_pages)
            case["anchoredPageCoverage"] = {
                "anchoredPages": len(anchored_pages),
                "declaredPages": declared_pages,
                "share": _share(len(anchored_pages), declared_pages),
                "missingPages": missing_pages,
            }
            referenced = set(facts_metrics["goldSectionsReferenced"])
            gold_headings = set(gold["h2Headings"])
            case["traceability"] = {
                "factsSchemaV3Valid": facts_metrics["schemaV3Valid"],
                "factsMetadataMatchesManifest": facts_metrics["metadataMatchesManifest"],
                "goldTitleMatchesManifest": gold["titleMatchesManifest"],
                "goldSectionsReferenced": len(referenced),
                "missingGoldSections": sorted(facts_metrics["missingGoldSections"]),
                "unreferencedGoldSections": sorted(gold_headings - referenced),
                "sourceAnchorCount": facts_metrics["sourceAnchorCount"],
                "sourceAnchorContradictionCount": facts_metrics["sourceAnchorContradictionCount"],
                "duplicateCanonicalClaims": sorted(facts_metrics["duplicateCanonicalClaims"]),
                "evidencePolicyCompletenessViolationCount": facts_metrics[
                    "evidencePolicyCompletenessViolationCount"
                ],
            }
        else:
            case["anchoredPageCoverage"]["declaredPages"] = declared_pages
        case["ok"] = not case["errors"]

    if manifest.get("pageCount") != declared_page_total:
        state.error(
            None,
            "MANIFEST_PAGE_COUNT_MISMATCH",
            "Manifest pageCount does not equal the sum of case page declarations.",
            actual=declared_page_total,
            declared=manifest.get("pageCount"),
        )

    report["suite"] = _aggregate_suite(report["cases"])
    report["ok"] = not state.errors
    return report


def _empty_suite() -> dict[str, Any]:
    return {
        "caseCount": 0,
        "declaredPages": 0,
        "physicalPages": 0,
        "physicalPageModalityCounts": _empty_counts(PHYSICAL_MODALITIES),
        "extractedWords": 0,
        "regionCount": 0,
        "leafCount": 0,
        "budget": 0,
        "budgetByModality": _empty_counts(SOURCE_LAYERS),
        "budgetByKind": _empty_counts(REGION_KINDS),
        "budgetByPrimaryAxis": _empty_counts(CAPABILITY_AXES),
        "textOnlyRecoverable": {"budget": 0, "totalBudget": 0, "budgetShare": 0.0},
        "anchoredPageCoverage": {"anchoredPages": 0, "declaredPages": 0, "share": 0.0, "missingPages": []},
        "traceability": {
            "casesPassingAllChecks": 0,
            "casesWithValidFactsV3": 0,
            "casesWithMatchingFactsMetadata": 0,
            "casesWithMatchingGoldTitle": 0,
            "sourceAnchorCount": 0,
            "sourceAnchorContradictionCount": 0,
            "missingGoldSectionCount": 0,
            "duplicateCanonicalClaimCount": 0,
            "evidencePolicyCompletenessViolationCount": 0,
        },
    }


def _aggregate_suite(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    suite = _empty_suite()
    suite["caseCount"] = len(cases)
    missing_page_refs: list[str] = []
    for case in cases:
        suite["declaredPages"] += int(case["anchoredPageCoverage"]["declaredPages"])
        suite["physicalPages"] += len(case["pages"])
        suite["extractedWords"] += int(case["extractedWords"])
        suite["regionCount"] += int(case["regionCount"])
        suite["leafCount"] += int(case["leafCount"])
        suite["budget"] += int(case["budget"])
        for key in PHYSICAL_MODALITIES:
            suite["physicalPageModalityCounts"][key] += int(case["physicalPageModalityCounts"].get(key, 0))
        for field, keys in (
            ("budgetByModality", SOURCE_LAYERS),
            ("budgetByKind", REGION_KINDS),
            ("budgetByPrimaryAxis", CAPABILITY_AXES),
        ):
            for key in keys:
                suite[field][key] += int(case[field].get(key, 0))
        suite["textOnlyRecoverable"]["budget"] += int(case["textOnlyRecoverable"]["budget"])
        suite["anchoredPageCoverage"]["anchoredPages"] += int(case["anchoredPageCoverage"]["anchoredPages"])
        for page_number in case["anchoredPageCoverage"]["missingPages"]:
            missing_page_refs.append(f"{case['id']}:p{page_number}")
        traceability = case["traceability"]
        suite_traceability = suite["traceability"]
        suite_traceability["casesPassingAllChecks"] += int(bool(case["ok"]))
        suite_traceability["casesWithValidFactsV3"] += int(bool(traceability["factsSchemaV3Valid"]))
        suite_traceability["casesWithMatchingFactsMetadata"] += int(bool(traceability["factsMetadataMatchesManifest"]))
        suite_traceability["casesWithMatchingGoldTitle"] += int(bool(traceability["goldTitleMatchesManifest"]))
        suite_traceability["sourceAnchorCount"] += int(traceability["sourceAnchorCount"])
        suite_traceability["sourceAnchorContradictionCount"] += int(traceability["sourceAnchorContradictionCount"])
        suite_traceability["missingGoldSectionCount"] += len(traceability["missingGoldSections"])
        suite_traceability["duplicateCanonicalClaimCount"] += len(traceability["duplicateCanonicalClaims"])
        suite_traceability["evidencePolicyCompletenessViolationCount"] += int(
            traceability["evidencePolicyCompletenessViolationCount"]
        )

    suite["textOnlyRecoverable"]["totalBudget"] = suite["budget"]
    suite["textOnlyRecoverable"]["budgetShare"] = _share(
        suite["textOnlyRecoverable"]["budget"], suite["budget"]
    )
    suite["anchoredPageCoverage"]["declaredPages"] = suite["declaredPages"]
    suite["anchoredPageCoverage"]["share"] = _share(
        suite["anchoredPageCoverage"]["anchoredPages"], suite["declaredPages"]
    )
    suite["anchoredPageCoverage"]["missingPages"] = missing_page_refs
    suite["budgetAccounting"] = _budget_accounting(cases, suite)
    return suite


def _serialize(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit physical PDF modalities and facts/gold/source traceability without provider calls."
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path("benchmark/manifest.json"),
        help="Path to the benchmark manifest JSON (default: benchmark/manifest.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Atomically write the same JSON report to this path in addition to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_manifest(args.manifest)
    serialized = _serialize(report)
    if args.output is not None:
        _atomic_write(args.output, serialized)
    sys.stdout.write(serialized)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
