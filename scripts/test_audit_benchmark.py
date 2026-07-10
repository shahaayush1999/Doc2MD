from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from scripts.audit_benchmark import _budget_accounting, _empty_suite, audit_manifest, main


def _region(
    region_id: str,
    page: int,
    layer: str,
    gold_section: str,
    *,
    budget: int,
    kind: str = "text",
    modality: str = "native_text",
    primary_axis: str = "precise_recall",
    text_only: bool = False,
) -> dict[str, object]:
    claim_type = "visual_description" if kind == "image" else "scalar"
    evidence_policy: dict[str, object]
    if claim_type == "visual_description":
        evidence_policy = {"type": "qualitative", "requiredTerms": [[region_id], [gold_section]]}
    else:
        evidence_policy = {"type": "lexical", "allOf": [[region_id], [gold_section]]}
    return {
        "id": region_id,
        "label": gold_section,
        "sourceAnchors": [{"page": page, "layer": layer, "sectionPath": [gold_section]}],
        "goldSection": gold_section,
        "kind": kind,
        "modality": modality,
        "uniqueEvidence": True,
        "primaryAxis": primary_axis,
        "secondaryAxes": [],
        "textOnlyRecoverable": text_only,
        "budget": budget,
        "leaves": [
            {
                "id": f"{region_id}.claim",
                "canonicalClaimId": f"{region_id}.canonical",
                "claimType": claim_type,
                "expectation": f"{region_id} records {gold_section}",
                "harm": 1,
                "evidencePolicy": evidence_policy,
            }
        ],
    }


class BenchmarkAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        case_dir = self.root / "cases" / "C1"
        case_dir.mkdir(parents=True)
        self.pdf = case_dir / "source.pdf"
        self.gold = case_dir / "gold.md"
        self.facts = case_dir / "facts.json"
        self.manifest = self.root / "manifest.json"
        self._write_pdf()
        self.gold.write_text(
            "# Audit Fixture\n\n## Native Evidence\n\nText.\n\n"
            "## Raster Evidence\n\nImage.\n\n## Mixed Evidence\n\nBoth.\n",
            encoding="utf-8",
        )
        facts = {
            "schemaVersion": 3,
            "id": "C1",
            "title": "Audit Fixture",
            "family": "test fixture",
            "tags": ["audit"],
            "regions": [
                _region("native", 1, "native_text", "Native Evidence", budget=1, text_only=True),
                _region(
                    "raster",
                    2,
                    "raster",
                    "Raster Evidence",
                    budget=2,
                    kind="image",
                    modality="raster",
                    primary_axis="image_description",
                ),
                _region("mixed", 3, "mixed", "Mixed Evidence", budget=3, kind="mixed", modality="mixed"),
            ],
        }
        self.facts.write_text(json.dumps(facts), encoding="utf-8")
        manifest = {
            "schemaVersion": 2,
            "name": "Fixture",
            "caseCount": 1,
            "pageCount": 3,
            "cases": [
                {
                    "id": "C1",
                    "title": "Audit Fixture",
                    "family": "test fixture",
                    "tags": ["audit"],
                    "pages": 3,
                    "pdf": "cases/C1/source.pdf",
                    "gold": "cases/C1/gold.md",
                    "facts": "cases/C1/facts.json",
                }
            ],
        }
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_pdf(self) -> None:
        width, height = letter
        document = canvas.Canvas(str(self.pdf), pagesize=letter, pageCompression=1)
        document.drawString(72, height - 72, "native page evidence")
        document.showPage()
        raster = Image.new("RGB", (612, 792), "white")
        document.drawImage(ImageReader(raster), 0, 0, width=width, height=height)
        document.showPage()
        document.drawString(72, height - 72, "mixed page evidence")
        document.drawImage(ImageReader(Image.new("RGB", (100, 100), "gray")), 72, height - 200, width=100, height=100)
        document.showPage()
        document.save()

    def test_reports_physical_modalities_budgets_and_traceability(self) -> None:
        report = audit_manifest(self.manifest)

        self.assertTrue(report["ok"], report["errors"])
        case = report["cases"][0]
        self.assertEqual(
            case["physicalPageModalityCounts"],
            {"native-only": 1, "full-page-raster": 1, "mixed": 1, "other": 0},
        )
        self.assertGreaterEqual(case["extractedWords"], 6)
        self.assertEqual((case["regionCount"], case["leafCount"], case["budget"]), (3, 3, 6))
        self.assertEqual(case["budgetByModality"]["native_text"], 1)
        self.assertEqual(case["budgetByModality"]["raster"], 2)
        self.assertEqual(case["budgetByModality"]["mixed"], 3)
        self.assertEqual(case["textOnlyRecoverable"], {"budget": 1, "totalBudget": 6, "budgetShare": 0.166667})
        self.assertEqual(
            case["anchoredPageCoverage"],
            {"anchoredPages": 3, "declaredPages": 3, "share": 1.0, "missingPages": []},
        )
        self.assertTrue(case["traceability"]["factsSchemaV3Valid"])
        self.assertEqual(case["traceability"]["sourceAnchorContradictionCount"], 0)
        self.assertEqual(report["suite"]["physicalPageModalityCounts"], case["physicalPageModalityCounts"])
        self.assertEqual(report["suite"]["traceability"]["casesPassingAllChecks"], 1)
        accounting = report["suite"]["budgetAccounting"]
        self.assertEqual(accounting["rawPooled"]["shareByModality"]["native_text"], 0.166667)
        self.assertEqual(accounting["equalCaseEffectiveShares"]["byModality"]["native_text"], 0.166667)
        self.assertEqual(accounting["equalCaseEffectiveShares"]["caseWeight"], 1.0)

    def test_equal_case_shares_do_not_pool_large_case_budgets(self) -> None:
        suite = _empty_suite()
        suite["budget"] = 10
        suite["budgetByModality"]["native_text"] = 1
        suite["budgetByModality"]["raster"] = 9
        suite["budgetByKind"]["text"] = 1
        suite["budgetByKind"]["image"] = 9
        suite["budgetByPrimaryAxis"]["precise_recall"] = 1
        suite["budgetByPrimaryAxis"]["image_description"] = 9
        suite["textOnlyRecoverable"]["budget"] = 1
        cases = [
            {
                "budget": 1,
                "budgetByModality": {"native_text": 1},
                "budgetByKind": {"text": 1},
                "budgetByPrimaryAxis": {"precise_recall": 1},
                "textOnlyRecoverable": {"budget": 1},
            },
            {
                "budget": 9,
                "budgetByModality": {"raster": 9},
                "budgetByKind": {"image": 9},
                "budgetByPrimaryAxis": {"image_description": 9},
                "textOnlyRecoverable": {"budget": 0},
            },
        ]

        accounting = _budget_accounting(cases, suite)

        self.assertEqual(accounting["rawPooled"]["shareByModality"]["native_text"], 0.1)
        self.assertEqual(accounting["rawPooled"]["shareByModality"]["raster"], 0.9)
        self.assertEqual(accounting["equalCaseEffectiveShares"]["byModality"]["native_text"], 0.5)
        self.assertEqual(accounting["equalCaseEffectiveShares"]["byModality"]["raster"], 0.5)
        self.assertEqual(accounting["equalCaseEffectiveShares"]["textOnlyRecoverable"], 0.5)

    def test_flags_duplicate_claim_unanchored_page_and_physical_contradictions(self) -> None:
        facts = json.loads(self.facts.read_text(encoding="utf-8"))
        facts["regions"][0]["sourceAnchors"][0]["layer"] = "raster"
        facts["regions"][1]["sourceAnchors"].append(
            {"page": 2, "layer": "native_layer_recovery", "sectionPath": ["Raster Evidence"]}
        )
        facts["regions"][1]["textOnlyRecoverable"] = True
        facts["regions"][2]["sourceAnchors"][0] = {
            "page": 1,
            "layer": "mixed",
            "sectionPath": ["Mixed Evidence"],
        }
        facts["regions"][2]["leaves"][0]["canonicalClaimId"] = "native.canonical"
        self.facts.write_text(json.dumps(facts), encoding="utf-8")

        report = audit_manifest(self.manifest)

        self.assertFalse(report["ok"])
        error_codes = {finding["code"] for finding in report["errors"]}
        self.assertIn("SOURCE_ANCHOR_PHYSICAL_CONTRADICTION", error_codes)
        self.assertIn("TEXT_ONLY_VISUAL_OR_RASTER", error_codes)
        self.assertIn("DUPLICATE_CANONICAL_CLAIM", error_codes)
        self.assertIn("UNANCHORED_PAGE", error_codes)
        case = report["cases"][0]
        self.assertEqual(case["anchoredPageCoverage"]["missingPages"], [3])
        contradiction_layers = {
            finding.get("layer")
            for finding in report["errors"]
            if finding["code"] == "SOURCE_ANCHOR_PHYSICAL_CONTRADICTION"
        }
        self.assertEqual(contradiction_layers, {"raster", "mixed", "native_layer_recovery"})
        self.assertEqual(case["traceability"]["duplicateCanonicalClaims"], ["native.canonical"])

    def test_rejects_policy_that_makes_one_of_two_required_values_optional(self) -> None:
        facts = json.loads(self.facts.read_text(encoding="utf-8"))
        leaf = facts["regions"][0]["leaves"][0]
        leaf["expectation"] = "Native recoveries are 96.0% and 98.0%."
        leaf["evidencePolicy"] = {
            "type": "lexical",
            "allOf": [["Native"], ["96.0%", "98.0%"]],
        }
        self.facts.write_text(json.dumps(facts), encoding="utf-8")

        report = audit_manifest(self.manifest)

        self.assertFalse(report["ok"])
        findings = [
            finding
            for finding in report["errors"]
            if finding["code"] == "LEAF_EVIDENCE_POLICY_SIGNAL_MISSING"
        ]
        self.assertEqual({finding["signal"] for finding in findings}, {"96.0", "98.0"})
        self.assertTrue(all("one-of alternative" in finding["reason"] for finding in findings))
        self.assertEqual(
            report["cases"][0]["traceability"]["evidencePolicyCompletenessViolationCount"],
            2,
        )
        self.assertEqual(report["suite"]["traceability"]["evidencePolicyCompletenessViolationCount"], 2)

    def test_output_is_atomic_and_matches_stdout(self) -> None:
        output = self.root / "reports" / "audit.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([str(self.manifest), "--output", str(output)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.read_text(encoding="utf-8"), stdout.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["schemaVersion"], 2)
        self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
