from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "benchmark"
CASE_ROOT = BENCHMARK_ROOT / "cases"
RENDER_ROOT = BENCHMARK_ROOT / "renders"


@dataclass
class Case:
    id: str
    slug: str
    title: str
    family: str
    tags: list[str]
    public: bool
    pages: list[str]
    terms: dict[str, list[str]]

    @property
    def case_id(self) -> str:
        return f"{self.id}-{self.slug}"


def p(*lines: str) -> str:
    return "\n".join(lines)


CASES: list[Case] = [
    Case(
        "D01",
        "policy-memo",
        "Clean Business Policy Memo",
        "text_structure",
        ["public", "born-digital", "nested-list", "header-footer"],
        True,
        [
            p(
                "# Acme Operations Memo",
                "Document ID: D01-POL-447",
                "Effective date: 2026-08-01",
                "Owner: Revenue Operations",
                "",
                "## Purpose",
                "This memo defines the weekly close procedure for partner-sourced revenue.",
                "The close owner must preserve ticket IDs, exception labels, and approval notes exactly.",
                "",
                "## Procedure",
                "1. Export the source ledger by 10:00 UTC each Monday.",
                "2. Reconcile Stripe, reseller, and manual invoice totals.",
                "3. Mark unresolved deltas as Exception R-7, Exception R-8, or Exception R-9.",
                "4. Send the final Markdown close note to #revops-close.",
                "",
                "### Required approvals",
                "- Finance reviewer: Priya Menon",
                "- Data reviewer: Omar Chen",
                "- Executive reviewer: Lina Patel",
                "",
                "> Boxed note: Do not summarize partner exceptions; copy the exception labels exactly.",
            ),
            p(
                "# Acme Operations Memo",
                "## Appendix A: Exception Labels",
                "",
                "| Label | Meaning | Default owner | SLA |",
                "| --- | --- | --- | --- |",
                "| Exception R-7 | Currency mismatch | Finance reviewer | 24h |",
                "| Exception R-8 | Missing reseller remittance | Partner ops | 48h |",
                "| Exception R-9 | Manual invoice not linked | Revenue systems | 24h |",
                "",
                "Footer policy: page numbers and the document ID may be preserved once, but repeated boilerplate should not replace body content.",
            ),
        ],
        {
            "text": ["Acme Operations Memo", "D01-POL-447", "partner-sourced revenue", "Exception R-8"],
            "structure": ["## Purpose", "## Procedure", "### Required approvals", "Appendix A"],
            "tables": ["Currency mismatch", "Missing reseller remittance", "Manual invoice not linked"],
        },
    ),
    Case(
        "D02",
        "api-docs",
        "Technical API Documentation Excerpt",
        "text_structure",
        ["born-digital", "code", "simple-table", "callout"],
        False,
        [
            p(
                "# Ledger Export API",
                "Version: 2026-07-15",
                "",
                "## Endpoint",
                "`POST /v2/ledger_exports` creates an asynchronous export job.",
                "",
                "### Request fields",
                "| Field | Type | Required | Notes |",
                "| --- | --- | --- | --- |",
                "| workspace_id | string | yes | Must match `ws_` prefix. |",
                "| period_start | date | yes | Inclusive ISO date. |",
                "| period_end | date | yes | Exclusive ISO date. |",
                "| include_voided | boolean | no | Defaults to false. |",
                "",
                "> Warning: `period_end` is exclusive even when the UI label says Through.",
            ),
            p(
                "## Example request",
                "```json",
                '{"workspace_id":"ws_north_01","period_start":"2026-06-01","period_end":"2026-07-01","include_voided":false}',
                "```",
                "",
                "## Response",
                "```json",
                '{"job_id":"job_7841","status":"queued","download_url":null}',
                "```",
                "",
                "Retry policy: clients should retry `429` after the `Retry-After` header and should not retry `400`.",
            ),
            p(
                "## Error codes",
                "| Code | Name | Retryable | Meaning |",
                "| --- | --- | --- | --- |",
                "| 400 | invalid_period | no | Date range failed validation. |",
                "| 401 | missing_auth | no | API key was absent or invalid. |",
                "| 409 | export_exists | yes | Identical export is still running. |",
                "| 429 | rate_limited | yes | Workspace exceeded burst limit. |",
                "",
                "The exact phrase `export_exists` must remain in monospace or plain text.",
            ),
            p(
                "## Webhook payload",
                "```ts",
                "type LedgerExportWebhook = {",
                "  job_id: string;",
                "  status: 'completed' | 'failed';",
                "  download_url: string | null;",
                "};",
                "```",
                "",
                "Security note: never expose the raw `OPENAI_API_KEY` or `GOOGLE_VERTEX_API_KEY` in logs.",
            ),
        ],
        {
            "text": ["Ledger Export API", "POST /v2/ledger_exports", "period_end", "export_exists"],
            "structure": ["## Endpoint", "### Request fields", "## Error codes", "## Webhook payload"],
            "tables": ["workspace_id", "period_start", "rate_limited", "Retryable"],
            "special": ["```json", "LedgerExportWebhook", "OPENAI_API_KEY"],
        },
    ),
    Case(
        "D03",
        "academic-paper",
        "Academic Paper Excerpt",
        "text_structure",
        ["born-digital", "multi-column", "math", "figure", "footnote"],
        False,
        [
            p(
                "# Layout-Aware Markdown Reconstruction",
                "Authors: Mira Halden, Arun Dev, Keiko Sato",
                "",
                "## Abstract",
                "We evaluate whether multimodal models can recover document reading order, table structure, and inline visual references from born-digital PDFs.",
                "The proposed metric, Doc2MD-F, combines block alignment with visual fact checks.",
                "",
                "Keywords: document parsing; Markdown; multimodal evaluation",
            ),
            p(
                "## 1. Introduction",
                "Faithful document conversion is different from question answering. A model can answer a local question while omitting most of the document.",
                "Our benchmark asks for a single Markdown artifact, not a summary.",
                "",
                "Footnote 1: We treat repeated page numbers as optional boilerplate.",
            ),
            p(
                "## 2. Method",
                "The block alignment score is defined as:",
                "$$S = 0.25T + 0.20R + 0.20Q + 0.10F + 0.10V + 0.10M + 0.05C$$",
                "where T is text fidelity, R is reading order, Q is table quality, F is form quality, V is visual fact quality, M is math/code quality, and C is Markdown cleanliness.",
                "",
                "[[DIAGRAM: Figure 1. Evaluation pipeline | PDF input > model conversion > Markdown parse > block alignment > family score | The family score prevents a high text score from hiding poor visual reconstruction.]]",
            ),
            p(
                "## 3. Results",
                "| Model | Text | Tables | Visuals | Overall |",
                "| --- | ---: | ---: | ---: | ---: |",
                "| Model A | 93.1 | 71.4 | 64.0 | 81.2 |",
                "| Model B | 90.5 | 88.2 | 52.5 | 82.6 |",
                "| Model C | 86.0 | 79.0 | 76.5 | 80.5 |",
                "",
                "Model B has the highest overall score but the lowest visual score.",
            ),
            p(
                "## References",
                "[1] Clark et al. Structured document evaluation. 2024.",
                "[2] Lin et al. Table grid similarity. 2025.",
                "[3] Nair and Gomez. Visual fact extraction for charts. 2026.",
            ),
        ],
        {
            "text": ["Layout-Aware Markdown Reconstruction", "Doc2MD-F", "single Markdown artifact", "Model B"],
            "structure": ["## Abstract", "## 1. Introduction", "## 2. Method", "## References"],
            "tables": ["Model A", "93.1", "88.2", "Visuals"],
            "visual": ["Evaluation pipeline", "family score", "poor visual reconstruction"],
            "special": ["$$S =", "Footnote 1"],
        },
    ),
    Case(
        "D04",
        "regulatory-report",
        "Regulatory Report Section",
        "text_structure",
        ["born-digital", "footnote", "deep-heading", "boxed-notice"],
        False,
        [
            p("# State Energy Resilience Review", "Report section: 4.2 Distribution Readiness", "Docket: SER-2026-14"),
            p("## 4.2.1 Scope", "This section covers transformer inventory, feeder inspection cadence, and emergency mutual-aid triggers."),
            p("### Finding A", "Inventory coverage is adequate for urban substations but below threshold for rural feeders RF-12 and RF-19."),
            p("### Finding B", "The mutual-aid trigger is currently set at 72 hours. Staff recommends changing it to 48 hours."),
            p("> Compliance notice: utilities must preserve the incident code SER-2026-14-B in public filings."),
            p("## Appendix 4B: Threshold Table", "| Metric | Current | Proposed |", "| --- | ---: | ---: |", "| Rural spare transformer coverage | 62% | 80% |", "| Mutual-aid trigger | 72h | 48h |", "| Feeder inspection interval | 18 mo | 12 mo |"),
        ],
        {
            "text": ["State Energy Resilience Review", "SER-2026-14", "RF-12", "SER-2026-14-B"],
            "structure": ["## 4.2.1 Scope", "### Finding A", "### Finding B", "Appendix 4B"],
            "tables": ["Rural spare transformer coverage", "62%", "80%", "12 mo"],
            "special": ["Compliance notice", "public filings"],
        },
    ),
    Case(
        "D05",
        "legal-contract",
        "Legal Contract Excerpt",
        "text_structure",
        ["born-digital", "nested-list", "signature-block"],
        False,
        [
            p("# Master Services Agreement", "Agreement No.: MSA-ARC-2026-09", "Parties: Arcwell Labs, Inc. and Northstar Data LLC"),
            p("## 1. Definitions", "1.1 `Confidential Information` means non-public business, technical, or financial information.", "1.2 `Deliverables` means the Markdown reports, audit logs, and benchmark manifests listed in Exhibit A."),
            p("## 2. Services", "2.1 Provider will perform document-conversion evaluation services.", "2.2 Provider will not use Customer data to train general-purpose models."),
            p("## 3. Acceptance", "(a) Customer has five business days to reject a deliverable.", "(b) Silence after five business days is deemed acceptance.", "(c) Rejected deliverables must cite a specific failed criterion."),
            p("## 4. Liability", "The aggregate liability cap is USD 250,000, excluding confidentiality breach and payment obligations."),
            p("## Signature Block", "Arcwell Labs, Inc.: __________________ Date: 2026-07-31", "Northstar Data LLC: ________________ Date: 2026-07-31"),
        ],
        {
            "text": ["Master Services Agreement", "MSA-ARC-2026-09", "Northstar Data LLC", "USD 250,000"],
            "structure": ["## 1. Definitions", "1.1", "## 3. Acceptance", "## Signature Block"],
            "special": ["Confidential Information", "Deliverables", "five business days"],
        },
    ),
    Case(
        "D06",
        "invoice",
        "Invoice With Line Items",
        "forms_tables",
        ["public", "form", "simple-table", "key-value"],
        True,
        [
            p(
                "# Invoice INV-2026-0719",
                "Vendor: Meridian Document Systems",
                "Bill To: Helio Analytics LLC",
                "Issue date: 2026-07-19",
                "Due date: 2026-08-18",
                "",
                "| Item | Qty | Unit price | Amount |",
                "| --- | ---: | ---: | ---: |",
                "| PDF reconstruction audit | 12 | $180.00 | $2,160.00 |",
                "| Table scoring setup | 1 | $950.00 | $950.00 |",
                "| Visual fact rubric review | 3 | $225.00 | $675.00 |",
                "",
                "Subtotal: $3,785.00",
                "Tax: $302.80",
                "Total due: $4,087.80",
                "Payment terms: Net 30 by ACH.",
            )
        ],
        {
            "text": ["INV-2026-0719", "Meridian Document Systems", "Helio Analytics LLC", "Net 30"],
            "tables": ["PDF reconstruction audit", "$2,160.00", "Visual fact rubric review"],
            "forms": ["Subtotal: $3,785.00", "Tax: $302.80", "Total due: $4,087.80"],
        },
    ),
    Case(
        "D07",
        "bank-statement",
        "Bank Statement With Repeated Headers",
        "tables",
        ["born-digital", "multi-page-table", "financial"],
        False,
        [
            p("# Bank Statement", "Account: 8842-1139", "Period: 2026-06-01 to 2026-06-30", "| Date | Description | Debit | Credit | Balance |", "| --- | --- | ---: | ---: | ---: |", "| 2026-06-03 | Deposit ACME PAYROLL |  | $7,400.00 | $12,812.44 |", "| 2026-06-04 | Transfer RENT | $2,650.00 |  | $10,162.44 |", "| 2026-06-09 | Card GROCER A-117 | $184.22 |  | $9,978.22 |"),
            p("# Bank Statement Continued", "| Date | Description | Debit | Credit | Balance |", "| --- | --- | ---: | ---: | ---: |", "| 2026-06-18 | Refund CLOUDHOST |  | $48.19 | $10,026.41 |", "| 2026-06-22 | Wire NEXUS LABS | $1,275.00 |  | $8,751.41 |", "| 2026-06-29 | Interest credit |  | $3.18 | $8,754.59 |", "Closing balance: $8,754.59"),
        ],
        {
            "text": ["Account: 8842-1139", "2026-06-01", "Closing balance"],
            "tables": ["Deposit ACME PAYROLL", "$7,400.00", "Wire NEXUS LABS", "$8,754.59"],
        },
    ),
    Case(
        "D08",
        "financial-statement",
        "Annual Report Financial Statement",
        "tables",
        ["public", "born-digital", "complex-table", "footnote"],
        True,
        [
            p("# Consolidated Statement of Operations", "Fiscal year ended December 31, 2026", "Amounts in millions, except per-share data.", "| Line item | 2026 | 2025 | 2024 |", "| --- | ---: | ---: | ---: |", "| Revenue | 812.4 | 699.1 | 612.8 |", "| Cost of revenue | (322.0) | (288.4) | (251.7) |", "| Gross profit | 490.4 | 410.7 | 361.1 |"),
            p("## Operating expenses", "| Expense | 2026 | 2025 | 2024 |", "| --- | ---: | ---: | ---: |", "| Research and development | 144.7 | 128.2 | 109.5 |", "| Sales and marketing | 98.6 | 91.4 | 84.1 |", "| General and administrative | 52.8 | 49.9 | 44.3 |", "| Total operating expenses | 296.1 | 269.5 | 237.9 |"),
            p("## Notes", "Net income for 2026 was 132.6 million.", "Footnote A: Foreign exchange reduced 2026 revenue by 8.3 million.", "Footnote B: Per-share data excludes anti-dilutive awards."),
        ],
        {
            "text": ["Consolidated Statement of Operations", "Amounts in millions", "Footnote A"],
            "tables": ["Revenue", "812.4", "Gross profit", "Total operating expenses", "296.1"],
            "special": ["anti-dilutive", "Foreign exchange"],
        },
    ),
    Case(
        "D09",
        "scientific-table",
        "Scientific Complex Table",
        "tables",
        ["born-digital", "complex-table", "symbols", "caption"],
        False,
        [
            p("# Table 2. Ablation Results", "Caption: Accuracy and calibration error across reconstruction variants.", "| Variant | Encoder | OCR source | F1 (%) | ECE (%) | Notes |", "| --- | --- | --- | ---: | ---: | --- |", "| A0 | ViT-B | native text | 84.2 | 7.1 | baseline |", "| A1 | ViT-L | native text | 87.9 | 5.8 | larger encoder |", "| A2 | ViT-L | raster only | 81.3 | 9.4 | no text layer |", "| A3 | ViT-L | hybrid | 89.1 | 4.9 | best overall |"),
            p("Symbols: ECE means expected calibration error. The dagger marker indicates p < 0.05.", "Finding: A3 hybrid has the highest F1 and lowest ECE.", "Footnote: Native text is unavailable for scanned documents."),
        ],
        {
            "text": ["Ablation Results", "expected calibration error", "p < 0.05"],
            "tables": ["A3", "hybrid", "89.1", "4.9", "raster only"],
            "special": ["dagger", "scanned documents"],
        },
    ),
    Case(
        "D10",
        "landscape-wide-table",
        "Landscape Wide Table",
        "tables",
        ["landscape", "wide-table", "born-digital"],
        False,
        [
            p("%%LANDSCAPE%%", "# Regional Capacity Grid", "| Region | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Owner |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |", "| North | 72 | 74 | 79 | 81 | 88 | 91 | 93 | 92 | 89 | 84 | 78 | 75 | N. Iqbal |", "| South | 61 | 63 | 67 | 70 | 73 | 76 | 79 | 80 | 77 | 72 | 68 | 64 | M. Chen |", "| West | 55 | 58 | 60 | 62 | 66 | 69 | 71 | 70 | 67 | 63 | 60 | 57 | L. Patel |", "Note: July North capacity is 93 and should not be confused with August North capacity 92."),
        ],
        {
            "text": ["Regional Capacity Grid", "July North capacity"],
            "tables": ["North", "93", "August", "N. Iqbal", "West"],
        },
    ),
    Case(
        "D11",
        "multi-page-table",
        "Multi-Page Table Continuation",
        "tables",
        ["multi-page-table", "repeated-header", "footnote"],
        False,
        [
            p("# Equipment Register", "Table 4 continues across pages. Do not merge serial numbers.", "| Serial | Site | Type | Status | Next inspection |", "| --- | --- | --- | --- | --- |", "| EQ-1001 | Ridge | Pump | active | 2026-08-12 |", "| EQ-1002 | Ridge | Valve | watch | 2026-08-14 |", "| EQ-1003 | Mesa | Sensor | active | 2026-08-16 |"),
            p("# Equipment Register Continued", "| Serial | Site | Type | Status | Next inspection |", "| --- | --- | --- | --- | --- |", "| EQ-1004 | Mesa | Pump | retired | none |", "| EQ-1005 | Valley | Valve | active | 2026-09-02 |", "| EQ-1006 | Valley | Sensor | watch | 2026-09-04 |"),
            p("# Equipment Register Continued", "| Serial | Site | Type | Status | Next inspection |", "| --- | --- | --- | --- | --- |", "| EQ-1007 | Harbor | Pump | active | 2026-09-10 |", "| EQ-1008 | Harbor | Sensor | active | 2026-09-10 |", "| EQ-1009 | Harbor | Valve | blocked | 2026-09-18 |"),
            p("# Equipment Register Continued", "| Serial | Site | Type | Status | Next inspection |", "| --- | --- | --- | --- | --- |", "| EQ-1010 | Prairie | Pump | active | 2026-10-01 |", "| EQ-1011 | Prairie | Valve | active | 2026-10-03 |", "| EQ-1012 | Prairie | Sensor | watch | 2026-10-05 |"),
            p("## Register Notes", "Footnote 1: `none` means the asset is retired and no inspection is scheduled.", "Footnote 2: Blocked Harbor valve EQ-1009 requires a safety review before inspection.", "Total active assets: 8"),
        ],
        {
            "text": ["Equipment Register", "Table 4 continues", "Total active assets: 8"],
            "tables": ["EQ-1001", "EQ-1009", "blocked", "Prairie", "EQ-1012"],
            "special": ["Footnote 1", "retired", "safety review"],
        },
    ),
    Case(
        "D12",
        "application-form",
        "Application Form",
        "forms_tables",
        ["public", "form", "checkbox", "key-value"],
        True,
        [
            p("# Vendor Onboarding Application", "Application ID: VND-2026-442", "Legal name: Cascade Metrics LLC", "Tax classification: Limited liability company", "Primary contact: Jordan Lee", "Email: ops@cascade.example", "", "Service category:", "- [x] Data processing", "- [ ] Facilities", "- [ ] Hardware supply", "- [x] Security review required"),
            p("## Banking and certification", "Bank country: United States", "ACH routing suffix: 1194", "Certification status: SOC 2 Type II complete", "Signature: Jordan Lee", "Signed date: 2026-07-22", "Blank field: DUNS number"),
        ],
        {
            "text": ["VND-2026-442", "Cascade Metrics LLC", "Jordan Lee"],
            "forms": ["Data processing", "Security review required", "SOC 2 Type II complete", "DUNS number"],
            "structure": ["## Banking and certification"],
        },
    ),
    Case(
        "D13",
        "lab-form",
        "Lab-Style Intake Form",
        "forms_tables",
        ["form", "checkbox", "dense-boxes"],
        False,
        [
            p("# Sample Intake Form", "Specimen ID: LAB-AX-771", "Patient name: REDACTED TEST RECORD", "Collected: 2026-07-01 09:40", "Received: 2026-07-01 11:05", "Priority: STAT", "", "Panels requested:", "- [x] CBC", "- [x] CMP", "- [ ] Lipid panel", "- [ ] Thyroid panel"),
            p("## Handling", "Temperature on arrival: 4 C", "Container: lavender top tube", "Hemolysis: none observed", "Technician initials: RK", "Warning: Do not infer any diagnosis from this sample form."),
        ],
        {
            "text": ["LAB-AX-771", "REDACTED TEST RECORD", "STAT", "RK"],
            "forms": ["CBC", "CMP", "Lipid panel", "Temperature on arrival: 4 C"],
            "special": ["Do not infer any diagnosis"],
        },
    ),
    Case(
        "D14",
        "tax-form",
        "Government Form Plus Instructions",
        "forms_tables",
        ["form", "checkbox", "instructions", "line-numbers"],
        False,
        [
            p("# Form C-204: Small Entity Climate Credit", "Tax year: 2026", "Entity legal name: Brookside Toolworks", "Employer ID suffix: 4821", "", "Line 1 Gross receipts: $1,284,000", "Line 2 Eligible clean-power spend: $86,400", "Line 3 Credit rate: 12%", "Line 4 Tentative credit: $10,368"),
            p("## Elections", "- [ ] Carry credit backward", "- [x] Carry credit forward", "- [x] Certify domestic equipment content", "- [ ] Claim disaster-zone increase", "Signature: M. Rivera", "Date: 2026-07-15"),
            p("## Instructions", "Attach Schedule C-204-A if Line 2 exceeds $100,000.", "Do not round Line 4 to the nearest thousand.", "If Carry credit forward is selected, retain records for seven years."),
        ],
        {
            "text": ["Form C-204", "Brookside Toolworks", "Employer ID suffix: 4821"],
            "forms": ["Line 4 Tentative credit: $10,368", "Carry credit forward", "domestic equipment content"],
            "special": ["Do not round Line 4", "seven years"],
        },
    ),
    Case(
        "D15",
        "expense-receipt",
        "Receipt Scan",
        "ocr_robustness",
        ["scan", "receipt", "mild-noise", "table"],
        False,
        [
            p("# Harbor Market Receipt", "Receipt ID: HM-44918", "Date: 2026-06-28 18:42", "Cashier: Lane 3", "| Item | Qty | Amount |", "| --- | ---: | ---: |", "| Field notebook | 2 | $15.98 |", "| USB-C cable | 1 | $11.49 |", "| Black coffee | 1 | $3.25 |", "Subtotal: $30.72", "Tax: $2.46", "Total: $33.18", "Payment: VISA ending 2041"),
        ],
        {
            "text": ["Harbor Market Receipt", "HM-44918", "VISA ending 2041"],
            "tables": ["Field notebook", "USB-C cable", "Black coffee"],
            "forms": ["Subtotal: $30.72", "Tax: $2.46", "Total: $33.18"],
        },
    ),
    Case(
        "D16",
        "slide-deck",
        "Short Slide Deck",
        "visual_layout",
        ["slide", "icons", "chart", "diagram"],
        False,
        [
            p("# Slide 1: Northstar Launch Plan", "Subtitle: July 2026 board review", "Presenter: Imani Rao"),
            p("# Slide 2: Strategic pillars", "- Pillar A: Faster document intake", "- Pillar B: Fewer manual corrections", "- Pillar C: Visible cost controls"),
            p("# Slide 3: Funnel snapshot", "[[CHART: Funnel conversion | Stage | Accounts | Lead=120;Trial=54;Paid=18 | Paid is 15 percent of lead volume.]]"),
            p("# Slide 4: Product architecture", "[[DIAGRAM: Product architecture | Upload > Parse > Reconstruct > Score > Review | The Review stage sends failures back to Parse.]]"),
            p("# Slide 5: Risks", "| Risk | Mitigation | Owner |", "| --- | --- | --- |", "| Table drift | typed table scorer | Nisha |", "| Chart omissions | visual fact tuples | Omar |", "| Cost spike | per-page budget | Lina |"),
            p("# Slide 6: Timeline", "July: calibration cases", "August: hidden suite", "September: leaderboard pilot", "October: refresh bank"),
            p("# Slide 7: Decision needed", "- Approve Core-25 scope", "- Approve one public calibration release", "- Defer OCR stress suite"),
            p("# Slide 8: Close", "The launch gate is score stability plus reviewer agreement, not model hype."),
        ],
        {
            "text": ["Northstar Launch Plan", "Strategic pillars", "Decision needed", "score stability"],
            "tables": ["Table drift", "visual fact tuples", "per-page budget"],
            "visual": ["Funnel conversion", "Paid is 15 percent", "Product architecture", "Review stage"],
        },
    ),
    Case(
        "D17",
        "marketing-brochure",
        "Marketing Brochure",
        "visual_layout",
        ["brochure", "non-manhattan", "callout", "image"],
        False,
        [
            p("# FieldOps Control Room", "Operate field teams from one daily command page.", "[[IMAGE: Hero image showing a dispatcher dashboard beside two technician route cards.]]", "Callout: Average dispatch delay reduced from 42 minutes to 18 minutes.", "CTA: Request the 14-day pilot."),
            p("## Feature blocks", "1. Live route board: see technician capacity by region.", "2. Exception inbox: group stuck jobs by missing part, customer delay, or safety review.", "3. Closeout packet: export work orders as Markdown or PDF.", "Quote: The route board replaced three spreadsheets in the first week."),
        ],
        {
            "text": ["FieldOps Control Room", "14-day pilot", "three spreadsheets"],
            "structure": ["## Feature blocks", "Live route board", "Exception inbox"],
            "visual": ["dispatcher dashboard", "technician route cards", "Average dispatch delay"],
        },
    ),
    Case(
        "D18",
        "infographic-timeline",
        "Infographic Timeline",
        "visual_layout",
        ["public", "infographic", "timeline", "icons"],
        True,
        [
            p("# Incident Response Timeline", "[[DIAGRAM: Timeline | 09:10 Alert received > 09:18 Customer impact confirmed > 09:27 Mitigation deployed > 09:52 Error rate normal > 10:15 Postmortem started | The longest gap is 25 minutes between mitigation deployed and error rate normal.]]", "Top metric: 42 minutes to stable state.", "Owner: Reliability team"),
        ],
        {
            "text": ["Incident Response Timeline", "42 minutes", "Reliability team"],
            "visual": ["09:10 Alert received", "09:27 Mitigation deployed", "09:52 Error rate normal", "longest gap is 25 minutes"],
        },
    ),
    Case(
        "D19",
        "dashboard-page",
        "Dashboard Business Report Page",
        "visual_layout",
        ["dashboard", "chart", "kpi", "table"],
        False,
        [
            p("# Weekly Revenue Dashboard", "KPI card: Net revenue $4.82M, up 6.4% week over week.", "KPI card: Gross retention 94.1%, down 0.6 points.", "[[CHART: Revenue by segment | Week | Revenue USD M | Enterprise=2.8,3.0,3.1,3.4;SMB=1.0,1.1,1.2,1.4 | Enterprise remains the larger segment in every week.]]"),
            p("## Watch list", "| Account | Signal | Owner |", "| --- | --- | --- |", "| Atlas Bank | renewal slipped | Priya |", "| Nova Retail | usage spike | Ken |", "| Juniper Works | support escalation | Mira |", "Side note: Nova Retail is an expansion candidate, not a churn risk."),
        ],
        {
            "text": ["Weekly Revenue Dashboard", "$4.82M", "Gross retention 94.1%"],
            "tables": ["Atlas Bank", "Nova Retail", "support escalation"],
            "visual": ["Revenue by segment", "Enterprise remains the larger segment", "SMB"],
        },
    ),
    Case(
        "D20",
        "chart-heavy-page",
        "Single Chart-Heavy Report Page",
        "visual_layout",
        ["public", "chart", "caption", "numeric-tolerance"],
        True,
        [
            p("# Figure 3. Latency by Pipeline Stage", "[[CHART: Latency by Pipeline Stage | Stage | Median ms | Upload=120;Parse=480;Reconstruct=920;Score=310 | Reconstruct is the slowest stage; Upload is the fastest stage.]]", "Caption: Median wall-clock latency from 10,000 production conversions.", "Annotation: Reconstruct exceeds Parse by 440 ms."),
        ],
        {
            "text": ["Figure 3. Latency by Pipeline Stage", "10,000 production conversions", "440 ms"],
            "visual": ["Reconstruct is the slowest", "Upload is the fastest", "Parse=480", "Score=310"],
        },
    ),
    Case(
        "D21",
        "scientific-figure",
        "Scientific Figure Page",
        "visual_layout",
        ["figure", "multi-panel", "caption", "labels"],
        False,
        [
            p("# Figure 5. Error Modes", "[[DIAGRAM: Multi-panel figure | Panel A: missed table header; Panel B: swapped reading order; Panel C: hallucinated chart trend; Panel D: omitted handwritten note | Panel C is the only panel involving an invented trend.]]", "Caption: Four common failure modes observed during document-to-Markdown reconstruction."),
            p("## In-text discussion", "Panel A is usually caused by merged cells. Panel B appears in two-column reports. Panel D appears in mildly annotated scans.", "Required citation: see Section 6.2 for mitigation details."),
        ],
        {
            "text": ["Figure 5. Error Modes", "Section 6.2", "mitigation details"],
            "visual": ["Panel A", "missed table header", "Panel C", "invented trend", "Panel D"],
        },
    ),
    Case(
        "D22",
        "math-note",
        "Math Lecture Note",
        "special_formatting",
        ["math", "theorem", "proof", "equations"],
        False,
        [
            p("# Lecture 12: Alignment Loss", "Definition: Let B be a set of gold blocks and P be predicted blocks.", "The alignment loss is zero only when every required block is matched once."),
            p("## Theorem 1", "If every block in B has a unique exact textual match in P and the reading order is preserved, then the block-order penalty is zero.", "Proof: The monotone alignment maps each gold index to the same predicted index order."),
            p("## Equations", "$$L = 1 - \\frac{|M|}{|B|}$$", "$$R = \\frac{2PR}{P+R}$$", "where M is the matched block set, P is precision, and R is recall."),
        ],
        {
            "text": ["Lecture 12: Alignment Loss", "Theorem 1", "monotone alignment"],
            "structure": ["## Theorem 1", "Proof:", "## Equations"],
            "special": ["$$L =", "\\frac{|M|}{|B|}", "$$R =", "precision"],
        },
    ),
    Case(
        "D23",
        "annotated-printout",
        "Printed Document With Light Handwriting",
        "ocr_robustness",
        ["scan", "handwriting-light", "stamp", "redline"],
        False,
        [
            p("# Change Approval Sheet", "Request ID: CHG-7782", "System: Billing export worker", "Planned window: 2026-07-28 02:00-03:00 UTC", "Risk level: Medium", "[[STAMP: APPROVED BY CAB - 2026-07-25]]"),
            p("## Handwritten annotations", "[[HANDWRITE: Move rollback owner from Eli to Nisha.]]", "[[HANDWRITE: Do not deploy if queue depth exceeds 900.]]", "Typed note: rollback command is `workerctl rollback billing-export`."),
        ],
        {
            "text": ["CHG-7782", "Billing export worker", "Medium", "workerctl rollback"],
            "visual": ["APPROVED BY CAB", "Move rollback owner from Eli to Nisha", "queue depth exceeds 900"],
        },
    ),
    Case(
        "D24",
        "newspaper-scan",
        "Historical Newspaper Scan",
        "ocr_robustness",
        ["scan", "multi-column", "mild-degradation", "caption"],
        False,
        [
            p("# The Harbor Chronicle", "Edition: March 14, 1932", "Headline: Ferry Service Restored After Winter Storm", "Subhead: Crews cleared the east pier before dawn.", "Column 1: The first ferry departed at 6:45 in the morning with twenty-seven passengers.", "Column 2: Dockmaster Elias Ward said the fog signal would remain active until Friday.", "Caption: Workers inspect the repaired gangway beside Pier 3."),
        ],
        {
            "text": ["The Harbor Chronicle", "March 14, 1932", "Ferry Service Restored", "twenty-seven passengers"],
            "structure": ["Headline", "Subhead", "Column 1", "Column 2", "Caption"],
            "visual": ["repaired gangway", "Pier 3"],
        },
    ),
    Case(
        "D25",
        "bilingual-document",
        "Bilingual Structured Document",
        "text_structure",
        ["bilingual", "form", "table", "non-english"],
        False,
        [
            p("# Aviso de Servicio / Service Notice", "Numero de caso: SRV-2026-55", "Cliente: Jardin Norte", "Fecha de visita: 2026-08-04", "Resumen: Se reemplazo el sensor de presion y se verifico la alarma.", "", "| Campo / Field | Valor / Value |", "| --- | --- |", "| Tecnico / Technician | Luis Romero |", "| Estado / Status | Completo / Complete |", "| Proxima visita / Next visit | 2026-11-04 |"),
            p("## Confirmaciones / Confirmations", "- [x] Equipo probado / Equipment tested", "- [x] Cliente informado / Customer informed", "- [ ] Pieza pendiente / Part pending", "Nota: No hay pieza pendiente aunque la casilla aparece sin seleccionar."),
        ],
        {
            "text": ["Aviso de Servicio", "SRV-2026-55", "Jardin Norte", "sensor de presion"],
            "tables": ["Luis Romero", "Completo", "2026-11-04"],
            "forms": ["Equipo probado", "Cliente informado", "Pieza pendiente", "sin seleccionar"],
        },
    ),
]


def case_dir(case: Case) -> Path:
    return CASE_ROOT / case.case_id


def marker_to_gold(line: str) -> list[str]:
    if line.startswith("[[CHART:"):
        body = line.removeprefix("[[CHART:").removesuffix("]]")
        parts = [part.strip() for part in body.split("|")]
        title = parts[0]
        facts = parts[-1] if len(parts) > 1 else ""
        return [f"![Chart: {title}. {facts}]"]
    if line.startswith("[[DIAGRAM:"):
        body = line.removeprefix("[[DIAGRAM:").removesuffix("]]")
        parts = [part.strip() for part in body.split("|")]
        title = parts[0]
        flow = parts[1] if len(parts) > 1 else ""
        note = parts[2] if len(parts) > 2 else ""
        return [f"![Diagram: {title}. Flow: {flow}. {note}]"]
    if line.startswith("[[IMAGE:"):
        body = line.removeprefix("[[IMAGE:").removesuffix("]]")
        return [f"![Image: {body}]"]
    if line.startswith("[[STAMP:"):
        body = line.removeprefix("[[STAMP:").removesuffix("]]")
        return [f"[Stamp: {body}]"]
    if line.startswith("[[HANDWRITE:"):
        body = line.removeprefix("[[HANDWRITE:").removesuffix("]]")
        return [f"[Handwritten note: {body}]"]
    if line == "%%LANDSCAPE%%":
        return []
    return [line]


def gold_markdown(case: Case) -> str:
    pages: list[str] = []
    for page_num, page in enumerate(case.pages, start=1):
        if page_num > 1:
            pages.append(f"\n<!-- page {page_num} -->\n")
        for line in page.splitlines():
            pages.extend(marker_to_gold(line))
    return "\n".join(pages).strip() + "\n"


def slugify_check(term: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", term.lower()).strip("-")
    return cleaned[:48] or "check"


def js_regex_escape(term: str) -> str:
    return re.sub(r"([\\.^$*+?{}\[\]|()])", r"\\\1", term)


def pattern_for_term(term: str) -> str:
    heading = re.match(r"^#+\s+(.+)$", term)
    if heading:
        return r"^#{1,6}\s+" + js_regex_escape(heading.group(1))
    if "=" in term and not term.strip().startswith("$$"):
        left, right = term.split("=", 1)
        return js_regex_escape(left.strip()) + r"[\s\S]{0,80}" + js_regex_escape(right.strip())
    if ":" in term:
        left, right = term.split(":", 1)
        return js_regex_escape(left.strip()) + r"[\s*_:\-]{0,20}" + js_regex_escape(right.strip())
    return js_regex_escape(term)


def make_checks(case: Case) -> dict:
    checks = []
    for category, terms in case.terms.items():
        for term in terms:
            checks.append(
                {
                    "id": f"{category}-{slugify_check(term)}",
                    "category": category,
                    "weight": 1,
                    "description": f"Output should preserve: {term}",
                    "patterns": [pattern_for_term(term)],
                }
            )
    checks.append(
        {
            "id": "markdown-has-heading",
            "category": "markdown",
            "weight": 1,
            "description": "Output should contain at least one Markdown heading.",
            "patterns": [r"^#\s"],
        }
    )
    checks.append(
        {
            "id": "no-json-wrapper",
            "category": "markdown",
            "weight": 1,
            "description": "Output should not be wrapped as JSON.",
            "mustNotPatterns": [r'^\s*\{[\s\S]*"markdown"'],
        }
    )
    return {
        "id": case.case_id,
        "title": case.title,
        "family": case.family,
        "tags": case.tags,
        "public": case.public,
        "checks": checks,
    }


def draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_chars: int, leading: float = 13) -> float:
    for part in wrap(text, max_chars) or [""]:
        c.drawString(x, y, part)
        y -= leading
    return y


def draw_table(c: canvas.Canvas, rows: list[str], x: float, y: float, width: float) -> float:
    parsed = []
    for row in rows:
        if set(row.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        parsed.append(cells)
    if not parsed:
        return y
    cols = max(len(row) for row in parsed)
    cell_w = width / cols
    row_h = 22
    c.setFont("Helvetica", 7.7)
    for r, cells in enumerate(parsed):
        yy = y - r * row_h
        fill = colors.HexColor("#e5e7eb") if r == 0 else colors.white
        c.setFillColor(fill)
        c.rect(x, yy - row_h + 5, width, row_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        for col in range(cols):
            c.rect(x + col * cell_w, yy - row_h + 5, cell_w, row_h, fill=0, stroke=1)
            value = cells[col] if col < len(cells) else ""
            c.drawString(x + col * cell_w + 3, yy - 10, value[: max(8, int(cell_w / 4.6))])
    return y - len(parsed) * row_h - 8


def parse_marker(line: str) -> list[str]:
    body = line.split(":", 1)[1].removesuffix("]]")
    return [part.strip() for part in body.split("|")]


def draw_chart(c: canvas.Canvas, line: str, x: float, y: float, width: float) -> float:
    parts = parse_marker(line)
    title = parts[0]
    x_axis = parts[1] if len(parts) > 1 else "X"
    y_axis = parts[2] if len(parts) > 2 else "Y"
    series = parts[3] if len(parts) > 3 else ""
    fact = parts[4] if len(parts) > 4 else ""
    h = 170
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(x, y - h, width, h, 8, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 14, y - 20, title)
    c.setFont("Helvetica", 8)
    c.drawString(x + 14, y - 35, f"{x_axis} vs {y_axis}")
    chart_x = x + 55
    chart_y = y - 130
    chart_w = width - 95
    chart_h = 75
    c.line(chart_x, chart_y, chart_x + chart_w, chart_y)
    c.line(chart_x, chart_y, chart_x, chart_y + chart_h)
    values = re.findall(r"([A-Za-z0-9 ]+)=([0-9.,]+)", series)
    max_v = 1.0
    parsed = []
    for name, nums in values:
        vals = [float(v) for v in nums.split(",") if v]
        parsed.append((name.strip(), vals))
        max_v = max(max_v, *vals)
    palette = [colors.HexColor("#2563eb"), colors.HexColor("#dc2626"), colors.HexColor("#0f766e")]
    if parsed:
        single_value_series = all(len(vals) == 1 for _, vals in parsed)
        if single_value_series:
            gap = chart_w / len(parsed)
            bar_w = min(42, gap * 0.45)
            for si, (name, vals) in enumerate(parsed):
                value = vals[0]
                bh = (value / max_v) * chart_h
                bx = chart_x + si * gap + (gap - bar_w) / 2
                c.setFillColor(palette[si % len(palette)])
                c.rect(bx, chart_y, bar_w, bh, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 7)
                c.drawCentredString(bx + bar_w / 2, chart_y + bh + 5, f"{value:g}")
                c.drawCentredString(bx + bar_w / 2, chart_y - 16, name[:18])
        else:
            bar_group_w = chart_w / max(len(parsed[0][1]), 1)
            bar_w = min(22, bar_group_w / (len(parsed) + 1))
            for si, (name, vals) in enumerate(parsed):
                c.setFillColor(palette[si % len(palette)])
                for i, value in enumerate(vals):
                    bh = (value / max_v) * chart_h
                    bx = chart_x + i * bar_group_w + 8 + si * bar_w
                    c.rect(bx, chart_y, bar_w, bh, fill=1, stroke=0)
                    c.setFillColor(colors.black)
                    c.setFont("Helvetica", 7)
                    c.drawCentredString(bx + bar_w / 2, chart_y + bh + 5, f"{value:g}")
                    c.setFillColor(palette[si % len(palette)])
                c.drawString(chart_x + si * 150, chart_y - 16, name[:22])
    c.setFillColor(colors.HexColor("#7f1d1d"))
    c.setFont("Helvetica", 8)
    c.drawString(x + 14, y - 153, fact[:110])
    c.setFillColor(colors.black)
    return y - h - 12


def draw_diagram(c: canvas.Canvas, line: str, x: float, y: float, width: float) -> float:
    parts = parse_marker(line)
    title = parts[0]
    flow = parts[1] if len(parts) > 1 else ""
    note = parts[2] if len(parts) > 2 else ""
    h = 160
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(x, y - h, width, h, 8, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 14, y - 20, title)
    nodes = [node.strip() for node in re.split(r">|;", flow) if node.strip()]
    if nodes:
        gap = width / len(nodes)
        for i, node in enumerate(nodes):
            nx = x + i * gap + 10
            c.setFillColor(colors.HexColor("#dbeafe"))
            c.roundRect(nx, y - 98, gap - 20, 52, 6, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 7)
            wrapped = wrap(node, max(10, int((gap - 24) / 4.4)))[:3]
            start_y = y - 62 - (len(wrapped) - 1) * 5
            for j, part in enumerate(wrapped):
                c.drawCentredString(nx + (gap - 20) / 2, start_y - j * 10, part)
            if i < len(nodes) - 1:
                c.line(nx + gap - 15, y - 72, nx + gap - 3, y - 72)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#7f1d1d"))
    c.drawString(x + 14, y - 134, note[:115])
    c.setFillColor(colors.black)
    return y - h - 12


def draw_image_box(c: canvas.Canvas, line: str, x: float, y: float, width: float) -> float:
    label = line.removeprefix("[[IMAGE:").removesuffix("]]")
    h = 120
    c.setFillColor(colors.HexColor("#ecfeff"))
    c.roundRect(x, y - h, width, h, 8, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 14, y - 22, "Image panel")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    draw_wrapped(c, label, x + 14, y - 44, 90, 12)
    return y - h - 12


def render_page(c: canvas.Canvas, case: Case, page_text: str, page_num: int) -> None:
    landscape_page = "%%LANDSCAPE%%" in page_text
    page_size = landscape(letter) if landscape_page else letter
    c.setPageSize(page_size)
    w, h = page_size
    margin = 0.55 * inch
    x = margin
    y = h - margin
    max_width = w - 2 * margin
    max_chars = int(max_width / 5.1)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(x, h - 24, f"{case.id} - {case.title} - page {page_num}")
    c.setFillColor(colors.black)
    table_buffer: list[str] = []
    code_mode = False
    for raw in page_text.splitlines():
        line = raw.rstrip()
        if line == "%%LANDSCAPE%%":
            continue
        if table_buffer and not line.startswith("|"):
            y = draw_table(c, table_buffer, x, y, max_width)
            table_buffer = []
        if line.startswith("|"):
            table_buffer.append(line)
            continue
        if line.startswith("[[CHART:"):
            y = draw_chart(c, line, x, y, max_width)
            continue
        if line.startswith("[[DIAGRAM:"):
            y = draw_diagram(c, line, x, y, max_width)
            continue
        if line.startswith("[[IMAGE:"):
            y = draw_image_box(c, line, x, y, max_width)
            continue
        if line.startswith("[[STAMP:"):
            c.setFillColor(colors.HexColor("#fee2e2"))
            c.setStrokeColor(colors.HexColor("#991b1b"))
            c.roundRect(x, y - 34, 230, 32, 4, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#991b1b"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 10, y - 22, line.removeprefix("[[STAMP:").removesuffix("]]"))
            c.setFillColor(colors.black)
            y -= 48
            continue
        if line.startswith("[[HANDWRITE:"):
            c.setFillColor(colors.HexColor("#1d4ed8"))
            c.setFont("Helvetica-Oblique", 10)
            y = draw_wrapped(c, "Handwritten: " + line.removeprefix("[[HANDWRITE:").removesuffix("]]"), x + 20, y, max_chars - 8, 13)
            c.setFillColor(colors.black)
            y -= 4
            continue
        if line.startswith("```"):
            code_mode = not code_mode
            c.setFont("Courier", 8.5)
            c.setFillColor(colors.HexColor("#111827"))
            c.drawString(x, y, line)
            y -= 12
            continue
        if code_mode:
            c.setFont("Courier", 8.5)
            c.setFillColor(colors.HexColor("#111827"))
            y = draw_wrapped(c, line, x + 10, y, max_chars - 6, 12)
            continue
        if line.startswith("# "):
            c.setFont("Helvetica-Bold", 18)
            c.setFillColor(colors.HexColor("#111827"))
            y = draw_wrapped(c, line[2:], x, y, max_chars, 22)
        elif line.startswith("## "):
            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(colors.HexColor("#111827"))
            y = draw_wrapped(c, line[3:], x, y, max_chars, 18)
        elif line.startswith("### "):
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(colors.HexColor("#111827"))
            y = draw_wrapped(c, line[4:], x, y, max_chars, 15)
        elif line.startswith(">"):
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(colors.HexColor("#7f1d1d"))
            y = draw_wrapped(c, line, x + 12, y, max_chars - 6, 12)
        elif not line:
            y -= 8
        else:
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
            y = draw_wrapped(c, line, x, y, max_chars, 12)
        y -= 2
    if table_buffer:
        draw_table(c, table_buffer, x, y, max_width)
    c.showPage()


def render_pdf(case: Case, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_num, page in enumerate(case.pages, start=1):
        render_page(c, case, page, page_num)
    c.save()


def write_case(case: Case) -> dict:
    out = case_dir(case)
    out.mkdir(parents=True, exist_ok=True)
    render_pdf(case, out / "source.pdf")
    (out / "gold.md").write_text(gold_markdown(case), encoding="utf-8")
    checks = make_checks(case)
    (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    return {
        "id": case.case_id,
        "title": case.title,
        "family": case.family,
        "tags": case.tags,
        "public": case.public,
        "pdf": f"benchmark/cases/{case.case_id}/source.pdf",
        "gold": f"benchmark/cases/{case.case_id}/gold.md",
        "checks": f"benchmark/cases/{case.case_id}/checks.json",
        "pages": len(case.pages),
    }


def main() -> None:
    if CASE_ROOT.exists():
        shutil.rmtree(CASE_ROOT)
    CASE_ROOT.mkdir(parents=True, exist_ok=True)
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "Doc2MD-Core-25",
        "version": "0.1.0",
        "description": "Synthetic first-pass Doc2MD benchmark with 25 diagnostic PDF-to-Markdown documents.",
        "caseCount": len(CASES),
        "pageCount": sum(len(case.pages) for case in CASES),
        "publicCaseCount": sum(1 for case in CASES if case.public),
        "cases": [write_case(case) for case in CASES],
    }
    (BENCHMARK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['caseCount']} cases and {manifest['pageCount']} pages to {BENCHMARK_ROOT}")


if __name__ == "__main__":
    main()
