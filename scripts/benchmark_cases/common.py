from __future__ import annotations

import json
import math
import random
import re
import reportlab
import textwrap
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


REPO_ROOT = Path(__file__).resolve().parents[2]
PORTRAIT = LETTER
LANDSCAPE = landscape(LETTER)

INK = HexColor("#17202A")
MUTED = HexColor("#59636E")
RULE = HexColor("#C9CED3")
LIGHT_RULE = HexColor("#E5E7E9")
PAPER = HexColor("#FCFCFA")
BLUE = HexColor("#1D4E89")
RED = HexColor("#9E2A2B")
AMBER = HexColor("#A15C00")
GREEN = HexColor("#2D6A4F")

FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"
REGULAR = "DocSans"
BOLD = "DocSans-Bold"
ITALIC = "DocSans-Italic"
pdfmetrics.registerFont(TTFont(REGULAR, str(FONT_DIR / "Vera.ttf")))
pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "VeraBd.ttf")))
pdfmetrics.registerFont(TTFont(ITALIC, str(FONT_DIR / "VeraIt.ttf")))


def slugify(value: str) -> str:
    return "-".join(part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def wrap_lines(text: str, width: float, font: str, size: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if pdfmetrics.stringWidth(candidate, font, size) <= width:
            current = candidate
        elif current:
            lines.append(current)
            current = ""
            # The next word can itself exceed the column. Split it here just
            # as we do for an overlong first word; otherwise a header such as
            # "requirement" can extend beyond the page after a wrapped word.
            for char in word:
                if pdfmetrics.stringWidth(current + char, font, size) <= width:
                    current += char
                else:
                    if current:
                        lines.append(current)
                    current = char
        else:
            # Preserve long identifiers while allowing them to wrap deterministically.
            chunk = ""
            for char in word:
                if pdfmetrics.stringWidth(chunk + char, font, size) <= width:
                    chunk += char
                else:
                    lines.append(chunk)
                    chunk = char
            current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def draw_paragraph(
    canvas: Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "DocSans",
    size: float = 9.2,
    leading: float = 12.2,
    color: Color = INK,
    max_lines: int | None = None,
) -> float:
    lines = wrap_lines(text, width, font, size)
    if max_lines is not None:
        if len(lines) > max_lines:
            raise ValueError(f"Paragraph would truncate {len(lines) - max_lines} line(s): {text[:80]!r}")
    canvas.setFont(font, size)
    canvas.setFillColor(color)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def draw_label(canvas: Canvas, text: str, x: float, y: float, *, color: Color = MUTED) -> None:
    canvas.setFillColor(color)
    canvas.setFont("DocSans-Bold", 6.8)
    canvas.drawString(x, y, text.upper())


def draw_badge(canvas: Canvas, text: str, x: float, y: float, color: Color) -> float:
    width = pdfmetrics.stringWidth(text.upper(), "DocSans-Bold", 7) + 14
    canvas.setFillColor(Color(color.red, color.green, color.blue, alpha=0.10))
    canvas.roundRect(x, y - 3, width, 15, 4, fill=1, stroke=0)
    canvas.setFillColor(color)
    canvas.setFont("DocSans-Bold", 7)
    canvas.drawString(x + 7, y + 1, text.upper())
    return width


def draw_checkbox(canvas: Canvas, x: float, y: float, state: str, label: str = "") -> None:
    canvas.setStrokeColor(INK if state != "disabled" else RULE)
    canvas.setLineWidth(0.8)
    canvas.rect(x, y, 9, 9, fill=0, stroke=1)
    if state == "checked":
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(1.4)
        canvas.line(x + 1.5, y + 4.5, x + 4, y + 1.5)
        canvas.line(x + 4, y + 1.5, x + 8.5, y + 8)
    elif state == "crossed":
        canvas.setStrokeColor(RED)
        canvas.line(x + 1, y + 1, x + 8, y + 8)
        canvas.line(x + 1, y + 8, x + 8, y + 1)
    elif state == "disabled":
        canvas.setFillColor(HexColor("#E8EAEC"))
        canvas.rect(x + 1, y + 1, 7, 7, fill=1, stroke=0)
    if label:
        canvas.setFillColor(INK if state != "disabled" else MUTED)
        canvas.setFont("DocSans", 8)
        canvas.drawString(x + 14, y + 1, label)


def draw_arrow(
    canvas: Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: Color = INK,
    dashed: bool = False,
    width: float = 1.4,
) -> None:
    canvas.saveState()
    canvas.setStrokeColor(color)
    canvas.setFillColor(color)
    canvas.setLineWidth(width)
    if dashed:
        canvas.setDash(5, 3)
    canvas.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 7
    left = angle + math.pi * 0.84
    right = angle - math.pi * 0.84
    path = canvas.beginPath()
    path.moveTo(x2, y2)
    path.lineTo(x2 + length * math.cos(left), y2 + length * math.sin(left))
    path.lineTo(x2 + length * math.cos(right), y2 + length * math.sin(right))
    path.close()
    canvas.drawPath(path, fill=1, stroke=0)
    canvas.restoreState()


def draw_table(
    canvas: Canvas,
    x: float,
    top: float,
    widths: Sequence[float],
    rows: Sequence[Sequence[str]],
    *,
    font_size: float = 7.2,
    row_padding: float = 4.2,
    header_rows: int = 1,
    group_header_rows: int = 0,
    zebra: bool = False,
    vertical_rules: bool = False,
) -> float:
    """Draw a compact, alignment-led table and return its lower y coordinate."""
    page_width = float(canvas._pagesize[0])
    if x < 0 or x + sum(widths) > page_width + 0.1:
        raise ValueError(f"Table exceeds page width: x={x}, width={sum(widths)}, page={page_width}")
    y = top
    line_height = font_size + 2.4
    for row_index, row in enumerate(rows):
        is_header = row_index < header_rows
        is_group = row_index < group_header_rows
        wrap_font = "DocSans-Bold" if is_header else "DocSans"
        cell_lines = [
            wrap_lines(str(value), widths[i] - 2 * row_padding, wrap_font, font_size)
            for i, value in enumerate(row)
        ]
        height = max(len(lines) for lines in cell_lines) * line_height + 2 * row_padding
        if is_group:
            canvas.setFillColor(HexColor("#E9EDF1"))
            canvas.rect(x, y - height, sum(widths), height, fill=1, stroke=0)
        elif is_header:
            canvas.setFillColor(HexColor("#F3F4F4"))
            canvas.rect(x, y - height, sum(widths), height, fill=1, stroke=0)
        elif zebra and row_index % 2:
            canvas.setFillColor(HexColor("#FAFAF8"))
            canvas.rect(x, y - height, sum(widths), height, fill=1, stroke=0)
        cursor = x
        for col_index, lines in enumerate(cell_lines):
            canvas.setFont("DocSans-Bold" if is_header else "DocSans", font_size)
            canvas.setFillColor(INK)
            text_y = y - row_padding - font_size
            for line in lines:
                canvas.drawString(cursor + row_padding, text_y, line)
                text_y -= line_height
            if vertical_rules and col_index > 0:
                canvas.setStrokeColor(LIGHT_RULE)
                canvas.setLineWidth(0.35)
                canvas.line(cursor, y, cursor, y - height)
            cursor += widths[col_index]
        canvas.setStrokeColor(INK if is_header else LIGHT_RULE)
        canvas.setLineWidth(0.75 if is_header else 0.35)
        canvas.line(x, y - height, x + sum(widths), y - height)
        y -= height
    if y < 36:
        raise ValueError(f"Table enters the footer margin: bottom={y:.1f}")
    return y


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    def safe(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    return "\n".join(
        [
            "| " + " | ".join(safe(value) for value in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(safe(value) for value in row) + " |" for row in rows),
        ]
    )


def leaf(
    leaf_id: str,
    expectation: str,
    *,
    harm: int = 1,
    canonical_claim_id: str | None = None,
    claim_type: str = "scalar",
    evidence: Sequence[str | Sequence[str]] | None = None,
    evidence_policy: dict[str, Any] | None = None,
    allow_partial: bool | None = None,
) -> dict[str, Any]:
    # ``allow_partial`` remains accepted while the case builders are migrated,
    # but facts v3 deliberately has no partial-credit status. Qualitative
    # descriptions must be decomposed into explicit component leaves instead.
    del allow_partial
    auto_evidence_policy = evidence_policy is None and evidence is None
    if evidence_policy is None:
        infer_claim_type = claim_type == "scalar"
        state_mentions = re.findall(r"\b(?:checked|unchecked|disabled|crossed(?:\s+out)?)\b", expectation, flags=re.IGNORECASE)
        form_match = re.fullmatch(
            r"(.+?)\s+(?:is|remains|was)\s+(checked|unchecked|disabled|crossed(?:\s+out)?)\.?",
            expectation.strip(),
            flags=re.IGNORECASE,
        )
        edge_match = re.search(
            r"\bfrom\s+(.+?)\s+(?:-|=)?>(?:\s+)?(.+?)(?:\s+for\s+|\.|$)|\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+for\s+|\.|$)",
            expectation.strip(),
            flags=re.IGNORECASE,
        )
        if infer_claim_type and form_match and len(state_mentions) == 1 and ";" not in expectation:
            label, raw_state = form_match.groups()
            state = "crossed" if raw_state.lower().startswith("crossed") else raw_state.lower()
            claim_type = "form_state"
            evidence_policy = {"type": "form_state", "label": [label.strip()], "state": state}
        elif infer_claim_type and edge_match:
            source = edge_match.group(1) or edge_match.group(3)
            destination = edge_match.group(2) or edge_match.group(4)
            claim_type = "directed_edge"
            evidence_policy = {
                "type": "directed_edge",
                "source": [source.strip()],
                "destination": [destination.strip()],
            }
        else:
            groups = _evidence_groups(expectation, evidence)
            evidence_policy = {"type": "lexical", "allOf": groups}
    return {
        "id": leaf_id,
        "canonicalClaimId": canonical_claim_id or leaf_id,
        "claimType": claim_type,
        "expectation": expectation,
        "harm": harm,
        "evidencePolicy": evidence_policy,
        "_autoEvidencePolicy": auto_evidence_policy,
    }


_EVIDENCE_STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "before", "belongs", "between",
    "candidate", "contains", "document", "during", "each", "field", "final", "from", "has", "have",
    "into", "marked", "must", "only", "page", "preserve", "preserved", "record", "region", "remains",
    "shown", "source", "state", "table", "that", "the", "their", "there", "this", "through", "value",
    "visible", "with", "written",
}


@dataclass(frozen=True)
class EvidenceSignal:
    """An independently falsifiable literal asserted by a leaf expectation."""

    kind: str
    value: str
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidencePolicyViolation:
    """A high-signal expectation literal that the policy does not guarantee."""

    signal: EvidenceSignal
    reason: str


_MONTHS = {
    "jan": (1, "Jan", "January"),
    "feb": (2, "Feb", "February"),
    "mar": (3, "Mar", "March"),
    "apr": (4, "Apr", "April"),
    "may": (5, "May", "May"),
    "jun": (6, "Jun", "June"),
    "jul": (7, "Jul", "July"),
    "aug": (8, "Aug", "August"),
    "sep": (9, "Sep", "September"),
    "oct": (10, "Oct", "October"),
    "nov": (11, "Nov", "November"),
    "dec": (12, "Dec", "December"),
}
_MONTH_PATTERN = "(?:" + "|".join(
    sorted({name for _, short, long in _MONTHS.values() for name in (short, long)}, key=len, reverse=True)
) + ")"
_ISO_DATE_RE = re.compile(r"(?<![A-Za-z0-9])\d{4}-\d{2}-\d{2}(?![A-Za-z0-9])")
_TEXT_DATE_RE = re.compile(
    rf"(?<![A-Za-z0-9])(?:\d{{1,2}}\s+{_MONTH_PATTERN}\s+\d{{4}}|"
    rf"{_MONTH_PATTERN}\s+\d{{1,2}},?\s+\d{{4}})(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)
_TIME_RE = re.compile(
    r"(?<![A-Za-z0-9])\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:UTC|GMT|MST|MDT|PST|PDT|PT))?(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)
_IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"(?=[A-Za-z0-9][A-Za-z0-9._/-]*[A-Za-z])(?=[A-Za-z0-9][A-Za-z0-9._/-]*\d)"
    r"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*|"
    r"[A-Z]{2,}[A-Z0-9]*(?:[-_/][A-Z0-9]+)*"
    r")(?![A-Za-z0-9])"
)
_SCALAR_RE = re.compile(
    r"(?<![A-Za-z0-9.])(?:(?<!-)[<>≤≥]=?\s*|[+-]\s*)?"
    r"\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][+-]?\d+)?"
)
_DIRECTION_RE = re.compile(r"(?<=\d)\s*(?:->|→|>)\s*(?=\d)|(?<=\d)\s*(?:<-|←|<)\s*(?=\d)")
_UNIT_RE = re.compile(
    r"(?<![A-Za-z])(?:ng\s*/\s*L|mg\s*/\s*dL|mg\s*/\s*L|[uµμ]g\s*/\s*L|"
    r"[uµμ]L|mL|psi|nm|[uµμ]m|mm|cm|kV|mA|kW|MHz|kHz|Hz|rpm|kg|"
    r"hours?|hrs?|minutes?|mins?|days?|seconds|secs?|ms|°\s*C|%)"
    r"(?![A-Za-z])",
    flags=re.IGNORECASE,
)
_SINGLE_LETTER_UNIT_RE = re.compile(r"(?<=\d)\s*(?:V|A|W|C|g|s)(?![A-Za-z0-9])")
_QUALIFIER_RE = re.compile(
    r"\b(?:crossed\s+out|not\s+applicable|quantifier|qualifier|final|draft|current|"
    r"superseded|accepted|rejected|approved|unapproved|open|closed|pending|released|"
    r"hold|held|quarantine|quarantined|required|optional|never|none|only|not|no|yes|"
    r"true|false|pass|passed|fail|failed|checked|unchecked|disabled|upper|lower|minimum|"
    r"maximum|before|after|above|below|within|outside|inclusive|exclusive|native|raster|"
    r"signed|unsigned|corrected|uncorrected|controlling|advisory|active|inactive)\b",
    flags=re.IGNORECASE,
)


def _span_overlaps(span: tuple[int, int], occupied: Sequence[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in occupied)


def _numeric_alternatives(value: str) -> tuple[str, ...]:
    compact_with_commas = re.sub(r"\s+", "", value)
    if "," in compact_with_commas and not re.fullmatch(
        r"[<>≤≥]?[=]?[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[eE][+-]?\d+)?",
        compact_with_commas,
    ):
        return ()
    compact = compact_with_commas.replace(",", "")
    match = re.fullmatch(r"([<>≤≥]=?|[+-])?(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", compact)
    if not match:
        return ()
    prefix, raw_number = match.groups()
    alternatives = [compact]
    try:
        normalized_number = format(Decimal(raw_number), "f")
        if "." in normalized_number:
            normalized_number = normalized_number.rstrip("0").rstrip(".")
        normalized = f"{prefix or ''}{normalized_number}"
        if normalized and normalized not in alternatives:
            alternatives.append(normalized)
        if prefix:
            alternatives.extend((f"{prefix} {raw_number}", f"{prefix} {normalized_number}"))
            unicode_prefix = {">=": "≥", "<=": "≤"}.get(prefix)
            if unicode_prefix:
                alternatives.extend((f"{unicode_prefix}{raw_number}", f"{unicode_prefix} {raw_number}"))
    except InvalidOperation:
        pass
    return tuple(alternatives)


def _date_alternatives(value: str) -> tuple[str, ...]:
    compact = " ".join(value.replace(",", " ").split())
    year: int
    month: int
    day: int
    if match := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", compact):
        year, month, day = map(int, match.groups())
    elif match := re.fullmatch(rf"(\d{{1,2}})\s+({_MONTH_PATTERN})\s+(\d{{4}})", compact, flags=re.IGNORECASE):
        day = int(match.group(1))
        month = _MONTHS[match.group(2)[:3].lower()][0]
        year = int(match.group(3))
    elif match := re.fullmatch(rf"({_MONTH_PATTERN})\s+(\d{{1,2}})\s+(\d{{4}})", compact, flags=re.IGNORECASE):
        month = _MONTHS[match.group(1)[:3].lower()][0]
        day = int(match.group(2))
        year = int(match.group(3))
    else:
        return ()
    short, long = next((short, long) for number, short, long in _MONTHS.values() if number == month)
    return tuple(
        dict.fromkeys(
            (
                f"{year:04d}-{month:02d}-{day:02d}",
                f"{day} {short} {year}",
                f"{day:02d} {short} {year}",
                f"{day} {long} {year}",
                f"{short} {day} {year}",
                f"{long} {day} {year}",
                f"{day} {short}",
                f"{day:02d} {short}",
                f"{day} {long}",
                f"{short} {day}",
                f"{long} {day}",
            )
        )
    )


def _signal_alternatives(kind: str, value: str) -> tuple[str, ...]:
    alternatives: list[str] = [value]
    if kind == "date":
        alternatives.extend(_date_alternatives(value))
    elif kind == "scalar":
        alternatives.extend(_numeric_alternatives(value))
    elif kind == "time":
        match = re.match(r"0(\d:\d{2}(?::\d{2})?)(.*)$", value)
        if match:
            alternatives.append(match.group(1) + match.group(2))
    elif kind == "unit":
        alternatives.extend(
            value.replace("µ", symbol).replace("μ", symbol).replace("u", symbol)
            for symbol in ("u", "µ", "μ")
            if any(marker in value for marker in ("u", "µ", "μ"))
        )
    elif kind == "direction":
        alternatives.extend(("->", "→", ">") if ">" in value or "→" in value else ("<-", "←", "<"))
    elif kind == "identifier":
        if "/" in value:
            alternatives.append(re.sub(r"\s*/\s*", " / ", value))
        if "-" in value:
            hyphens = [index for index, char in enumerate(value) if char == "-"]
            if len(hyphens) <= 4:
                for mask in range(1, 1 << len(hyphens)):
                    characters = list(value)
                    for bit, index in enumerate(hyphens):
                        if mask & (1 << bit):
                            characters[index] = " "
                    alternatives.append("".join(characters))
    elif kind == "qualifier":
        aliases = {
            "maximum": ("max",),
            "minimum": ("min",),
            "within": ("+/-", "±"),
            "not": ("no", "without", "absent"),
            "no": ("not", "none", "without", "absent"),
            "final": ("finalized",),
            "accepted": ("accept",),
            "rejected": ("reject",),
            "current": ("controlling",),
            "controlling": ("current", "controls"),
            "crossed out": ("crossed",),
            "not applicable": ("N/A", "NA"),
            "open": ("unresolved", "outstanding"),
            "closed": ("resolved", "completed"),
            "pending": ("awaiting", "not final"),
            "hold": ("held", "on hold", "not released", "blocked"),
            "held": ("hold", "on hold", "not released", "blocked"),
            "above": ("over", "more than", "greater than", "exceeds", ">"),
            "below": ("under", "less than", "fewer than", "<"),
            "before": ("prior to", "earlier than"),
            "after": ("following", "later than"),
            "only": ("solely", "exclusively"),
        }
        alternatives.extend(aliases.get(value.casefold(), ()))
    return tuple(dict.fromkeys(item.strip() for item in alternatives if item.strip()))


def extract_evidence_signals(expectation: str) -> list[EvidenceSignal]:
    """Extract literals whose omission can make a lexical gate accept a wrong claim.

    The extractor is deliberately conservative about ordinary prose. It targets
    values where exact identity matters: dates, times, identifiers, numeric
    scalars, units, direction/sign markers, and finite-state qualifiers.
    """

    signals: list[EvidenceSignal] = []
    seen: set[tuple[str, str]] = set()
    occupied: list[tuple[int, int]] = []

    def add(kind: str, value: str, span: tuple[int, int] | None = None, *, protect: bool = False) -> None:
        compact = " ".join(value.split()).strip(" .,;:")
        if not compact:
            return
        key = (kind, _normalized_evidence_text(compact))
        if key not in seen:
            seen.add(key)
            signals.append(EvidenceSignal(kind, compact, _signal_alternatives(kind, compact)))
        if protect and span is not None:
            occupied.append(span)

    for pattern, kind in ((_ISO_DATE_RE, "date"), (_TEXT_DATE_RE, "date"), (_TIME_RE, "time")):
        for match in pattern.finditer(expectation):
            if not _span_overlaps(match.span(), occupied):
                add(kind, match.group(0), match.span(), protect=True)

    for match in _IDENTIFIER_RE.finditer(expectation):
        if not _span_overlaps(match.span(), occupied):
            add("identifier", match.group(0), match.span(), protect=True)

    for match in _SCALAR_RE.finditer(expectation):
        if not _span_overlaps(match.span(), occupied):
            add("scalar", match.group(0), match.span())

    for match in _UNIT_RE.finditer(expectation):
        unit = re.sub(r"\s*/\s*", "/", re.sub(r"°\s+", "°", match.group(0)))
        if re.fullmatch(r"hours?|hrs?|minutes?|mins?|days?|seconds?|secs?", unit, flags=re.IGNORECASE):
            nearby = expectation[max(0, match.start() - 12) : min(len(expectation), match.end() + 12)]
            if not any(char.isdigit() for char in nearby):
                continue
        add("unit", unit)
    for match in _SINGLE_LETTER_UNIT_RE.finditer(expectation):
        add("unit", match.group(0).strip())
    for match in _DIRECTION_RE.finditer(expectation):
        add("direction", match.group(0).strip())
    for match in _QUALIFIER_RE.finditer(expectation):
        add("qualifier", match.group(0))
    return signals


def _term_alternatives(value: str) -> list[str]:
    alternatives = [value]
    without_thousands_separators = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", value)
    if without_thousands_separators != value:
        alternatives.append(without_thousands_separators)
    numeric = _numeric_alternatives(value)
    alternatives.extend(numeric)
    if "→" in value:
        alternatives.append(value.replace("→", "->"))
    if "←" in value:
        alternatives.append(value.replace("←", "<-"))
    if "–" in value or "—" in value:
        alternatives.append(value.replace("–", "-").replace("—", "-"))
    return list(dict.fromkeys(item.strip() for item in alternatives if item.strip()))


def _evidence_groups(
    expectation: str,
    explicit: Sequence[str | Sequence[str]] | None,
) -> list[list[str]]:
    if explicit is not None:
        groups: list[list[str]] = []
        for value in explicit:
            if isinstance(value, str):
                groups.append(_term_alternatives(value))
            else:
                alternatives = list(
                    dict.fromkeys(
                        alternative
                        for item in value
                        for alternative in _term_alternatives(str(item))
                    )
                )
                if not alternatives:
                    raise ValueError(f"Evidence group for {expectation!r} is empty")
                groups.append(alternatives)
        if not groups:
            raise ValueError(f"Evidence for {expectation!r} must contain at least one group")
        return groups

    normalized = expectation.replace("→", " -> ")
    groups: list[list[str]] = []
    for signal in extract_evidence_signals(expectation):
        group = list(
            dict.fromkeys(
                alternative
                for value in signal.alternatives or (signal.value,)
                for alternative in _term_alternatives(value)
            )
        )
        if group and group not in groups:
            groups.append(group)

    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z-]{3,}", normalized)
        if word.lower() not in _EVIDENCE_STOPWORDS
    ]
    added_words = 0
    for word in sorted(dict.fromkeys(words), key=lambda item: (-len(item), words.index(item))):
        if not any(word in alternative.lower() for group in groups for alternative in group):
            groups.append([word])
            added_words += 1
        if added_words >= 3:
            break
    if not groups:
        compact = " ".join(expectation.split()).strip(" .")
        groups = [[compact]]
    return groups


def _normalized_evidence_text(value: str) -> str:
    normalized = (
        value.casefold()
        .replace("→", "->")
        .replace("←", "<-")
        .replace("≤", "<=")
        .replace("≥", ">=")
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("×", "x")
    )
    normalized = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", normalized)
    normalized = re.sub(r"[|*_`#]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _evidence_alternative_present(text: str, alternative: str) -> bool:
    normalized = _normalized_evidence_text(alternative)
    if not normalized:
        return False
    start = r"(?<![a-z0-9])" if normalized[0].isalnum() else ""
    end = r"(?![a-z0-9])" if normalized[-1].isalnum() else ""
    return re.search(start + re.escape(normalized) + end, text) is not None


def _policy_term_groups(policy: dict[str, Any]) -> list[list[str]]:
    policy_type = policy.get("type")
    if policy_type == "lexical":
        raw_groups = policy.get("allOf")
    elif policy_type == "ordered_tokens":
        raw_groups = policy.get("tokens")
    elif policy_type == "qualitative":
        raw_groups = policy.get("requiredTerms")
    elif policy_type == "table_binding":
        raw_groups = [policy.get("row"), policy.get("column"), policy.get("value")]
    elif policy_type == "form_state":
        raw_groups = [policy.get("label"), [policy.get("state")]]
    elif policy_type == "directed_edge":
        raw_groups = [policy.get("source"), policy.get("destination")]
        if "relation" in policy:
            raw_groups.append(policy.get("relation"))
    else:
        return []
    if not isinstance(raw_groups, list):
        return []
    return [
        [str(alternative).strip() for alternative in group if str(alternative).strip()]
        for group in raw_groups
        if isinstance(group, list) and group
    ]


def _alternative_guarantees_signal(alternative: str, signal: EvidenceSignal) -> bool:
    normalized = _normalized_evidence_text(alternative)
    return any(
        _evidence_alternative_present(normalized, signal_alternative)
        for signal_alternative in signal.alternatives or (signal.value,)
    )


def _alternative_is_yearless_form_of_date(alternative: str, signal: EvidenceSignal) -> bool:
    """Recognize an explicit packet-local date shorthand in a one-of group.

    A yearless form is accepted only by the group-level completeness check
    when another alternative in that same mandatory group carries the full
    audited date. This keeps the year mandatory while allowing a candidate to
    reproduce the literal source-table form under an unambiguous packet year.
    """
    if signal.kind != "date" or re.search(r"\b\d{4}\b", alternative):
        return False
    expanded = _date_alternatives(signal.value)
    if not expanded or not (iso := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", expanded[0])):
        return False
    _year, month_number, day_number = map(int, iso.groups())
    _number, short, long = next(item for item in _MONTHS.values() if item[0] == month_number)
    month = rf"(?:{re.escape(short)}|{re.escape(long)})"
    return bool(
        re.search(rf"(?<![A-Za-z0-9])0?{day_number}\s+{month}(?!\s+\d{{4}})", alternative, flags=re.IGNORECASE)
        or re.search(rf"(?<![A-Za-z0-9]){month}\s+0?{day_number}(?!,?\s+\d{{4}})", alternative, flags=re.IGNORECASE)
    )


def evidence_policy_violations(
    expectation: str,
    policy: dict[str, Any],
) -> list[EvidencePolicyViolation]:
    """Return expectation literals that are optional or absent under a policy.

    A signal is guaranteed only when at least one required group contains it in
    *every* alternative. This rejects the dangerous pattern ``[["96", "98"]]``
    for an expectation that requires both values, while accepting formatting
    alternatives such as ``[["1 ng/L", "1ng/L"]]``.
    """

    groups = _policy_term_groups(policy)
    violations: list[EvidencePolicyViolation] = []
    for signal in extract_evidence_signals(expectation):
        if policy.get("type") in {"directed_edge", "ordered_tokens"} and signal.kind == "direction":
            # Direction/order is structural in these typed policies; it is not
            # a lexical token and therefore need not be repeated as a term.
            continue
        guaranteeing_group = any(
            bool(group)
            and (
                all(_alternative_guarantees_signal(alternative, signal) for alternative in group)
                or (
                    signal.kind == "date"
                    and any(_alternative_guarantees_signal(alternative, signal) for alternative in group)
                    and all(
                        _alternative_guarantees_signal(alternative, signal)
                        or _alternative_is_yearless_form_of_date(alternative, signal)
                        for alternative in group
                    )
                )
            )
            for group in groups
        )
        if guaranteeing_group:
            continue
        mentioned_optionally = any(
            _alternative_guarantees_signal(alternative, signal)
            for group in groups
            for alternative in group
        )
        reason = (
            "the signal appears only in a non-mandatory one-of alternative"
            if mentioned_optionally
            else "the signal is absent from every mandatory policy group"
        )
        violations.append(EvidencePolicyViolation(signal, reason))
    return violations


def _refine_auto_lexical_policy(leaf_item: dict[str, Any], gold_section: str) -> None:
    policy = leaf_item.get("evidencePolicy", {})
    if policy.get("type") != "lexical":
        return
    normalized_gold = _normalized_evidence_text(gold_section)
    expectation = str(leaf_item["expectation"])
    candidate_groups = _evidence_groups(expectation, None)
    supported = [
        group
        for group in candidate_groups
        if any(_evidence_alternative_present(normalized_gold, alternative) for alternative in group)
    ]
    # Ordinary prose anchors are chosen opportunistically to make the lexical
    # gate local. High-signal literals are different: silently discarding one
    # changes the truth conditions of the leaf, so fail generation instead.
    provisional_policy = {"type": "lexical", "allOf": supported}
    unsupported_signals = evidence_policy_violations(expectation, provisional_policy)
    if unsupported_signals:
        raise ValueError(
            f"{leaf_item['id']}: high-signal expectation literal(s) are absent from its gold section: "
            + ", ".join(f"{item.signal.kind}={item.signal.value!r}" for item in unsupported_signals)
        )
    if not supported:
        raise ValueError(f"{leaf_item['id']}: no automatically selected evidence term occurs in its gold section")
    policy["allOf"] = supported
    violations = evidence_policy_violations(expectation, policy)
    if violations:
        rendered = ", ".join(f"{item.signal.kind}={item.signal.value!r}" for item in violations)
        raise ValueError(f"{leaf_item['id']}: automatic evidence policy is incomplete: {rendered}")


def _markdown_table_inventory(section: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = section.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []

    def cells(line: str) -> list[str] | None:
        if "|" not in line:
            return None
        values = [value.strip() for value in line.strip().strip("|").split("|")]
        return values if len(values) >= 2 else None

    def delimiter(values: list[str]) -> bool:
        return bool(values) and all(re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) for value in values)

    index = 0
    while index + 1 < len(lines):
        headers = cells(lines[index])
        rule = cells(lines[index + 1])
        if not headers or not rule or len(headers) != len(rule) or not delimiter(rule):
            index += 1
            continue
        rows: list[list[str]] = []
        row_index = index + 2
        while row_index < len(lines):
            row = cells(lines[row_index])
            if not row or len(row) != len(headers) or delimiter(row):
                break
            rows.append(row)
            row_index += 1
        tables.append((headers, rows))
        index = row_index
    return tables


def _expand_closed_world_table_keys(region: dict[str, Any], gold_section: str) -> None:
    closed_world = region.get("closedWorld")
    if not isinstance(closed_world, dict) or closed_world.get("scope") != "table_rows":
        return
    declared = [str(key) for key in closed_world.get("keys", [])]
    column_groups = [
        [str(value) for value in policy.get("column", [])]
        for leaf_item in region.get("leaves", [])
        if isinstance((policy := leaf_item.get("evidencePolicy")), dict)
        and policy.get("type") == "table_binding"
    ]
    if len(declared) < 2 or len(column_groups) < 2:
        return

    normalized_declared = {_normalized_evidence_text(key) for key in declared}
    matches: list[list[str]] = []
    for headers, rows in _markdown_table_inventory(gold_section):
        normalized_headers = {_normalized_evidence_text(header) for header in headers}
        matched_columns = sum(
            any(_normalized_evidence_text(alternative) in normalized_headers for alternative in group)
            for group in column_groups
        )
        row_keys = [row[0].strip() for row in rows if row and row[0].strip()]
        normalized_rows = {_normalized_evidence_text(key) for key in row_keys}
        if len(normalized_declared & normalized_rows) >= 2 and matched_columns >= 2:
            matches.append(row_keys)

    if len(matches) > 1:
        raise ValueError(f"{region.get('id')}: closed-world table matches multiple gold tables")
    if len(matches) == 1:
        closed_world["keys"] = list(dict.fromkeys(matches[0]))


def finalize_fact_regions(regions: Sequence[dict[str, Any]], gold: str) -> None:
    """Finalize generator metadata and evidence gates against audited gold."""
    headings = list(re.finditer(r"^## (.+)$", gold, flags=re.MULTILINE))
    sections = {
        match.group(1).strip(): gold[
            match.end() : headings[index + 1].start() if index + 1 < len(headings) else len(gold)
        ]
        for index, match in enumerate(headings)
    }
    failures: list[str] = []
    for region in regions:
        section_name = str(region.get("goldSection", ""))
        if section_name not in sections:
            failures.append(f"{region.get('id')}: gold section {section_name!r} is missing")
            continue
        try:
            _expand_closed_world_table_keys(region, sections[section_name])
        except ValueError as exc:
            failures.append(str(exc))
            continue
        for leaf_item in region.get("leaves", []):
            auto_policy = bool(leaf_item.pop("_autoEvidencePolicy", False))
            if auto_policy:
                try:
                    _refine_auto_lexical_policy(leaf_item, sections[section_name])
                except ValueError as exc:
                    failures.append(str(exc))
                    continue
            policy = leaf_item.get("evidencePolicy")
            if isinstance(policy, dict):
                violations = evidence_policy_violations(str(leaf_item.get("expectation", "")), policy)
                if violations:
                    rendered = ", ".join(
                        f"{item.signal.kind}={item.signal.value!r} ({item.reason})"
                        for item in violations
                    )
                    failures.append(f"{leaf_item.get('id')}: evidence policy is incomplete: {rendered}")
    if failures:
        raise ValueError("Evidence-policy finalization failed:\n- " + "\n- ".join(failures))


def form_state_leaf(
    leaf_id: str,
    expectation: str,
    label: str | Sequence[str],
    state: str,
    *,
    harm: int = 1,
    canonical_claim_id: str | None = None,
) -> dict[str, Any]:
    labels = [label] if isinstance(label, str) else list(label)
    return leaf(
        leaf_id,
        expectation,
        harm=harm,
        canonical_claim_id=canonical_claim_id,
        claim_type="form_state",
        evidence_policy={"type": "form_state", "label": labels, "state": state},
    )


def directed_edge_leaf(
    leaf_id: str,
    expectation: str,
    source: str | Sequence[str],
    destination: str | Sequence[str],
    *,
    relation: str | Sequence[str] | None = None,
    harm: int = 1,
    canonical_claim_id: str | None = None,
) -> dict[str, Any]:
    sources = [source] if isinstance(source, str) else list(source)
    destinations = [destination] if isinstance(destination, str) else list(destination)
    policy: dict[str, Any] = {"type": "directed_edge", "source": sources, "destination": destinations}
    if relation is not None:
        policy["relation"] = [relation] if isinstance(relation, str) else list(relation)
    return leaf(
        leaf_id,
        expectation,
        harm=harm,
        canonical_claim_id=canonical_claim_id,
        claim_type="directed_edge",
        evidence_policy=policy,
    )


def visual_leaf(
    leaf_id: str,
    expectation: str,
    required_terms: Sequence[str | Sequence[str]],
    *,
    harm: int = 1,
    canonical_claim_id: str | None = None,
) -> dict[str, Any]:
    return leaf(
        leaf_id,
        expectation,
        harm=harm,
        canonical_claim_id=canonical_claim_id,
        claim_type="visual_description",
        evidence_policy={"type": "qualitative", "requiredTerms": _evidence_groups(expectation, required_terms)},
    )


def source_precedence_leaf(
    leaf_id: str,
    expectation: str,
    ordered_tokens: Sequence[str | Sequence[str]],
    *,
    harm: int = 2,
    canonical_claim_id: str | None = None,
) -> dict[str, Any]:
    return leaf(
        leaf_id,
        expectation,
        harm=harm,
        canonical_claim_id=canonical_claim_id,
        claim_type="source_precedence",
        evidence_policy={"type": "ordered_tokens", "tokens": _evidence_groups(expectation, ordered_tokens)},
    )


def table_binding_leaf(
    leaf_id: str,
    expectation: str,
    row: str | Sequence[str],
    column: str | Sequence[str],
    value: str | Sequence[str],
    *,
    harm: int = 1,
    canonical_claim_id: str | None = None,
) -> dict[str, Any]:
    """Build one atomic row/column/value obligation with format aliases."""

    def alternatives(item: str | Sequence[str]) -> list[str]:
        values = [item] if isinstance(item, str) else list(item)
        return list(
            dict.fromkeys(
                alternative
                for raw_value in values
                for alternative in _term_alternatives(str(raw_value))
            )
        )

    return leaf(
        leaf_id,
        expectation,
        harm=harm,
        canonical_claim_id=canonical_claim_id,
        claim_type="table_binding",
        evidence_policy={
            "type": "table_binding",
            "row": alternatives(row),
            "column": alternatives(column),
            "value": alternatives(value),
        },
    )


def table_leaves(
    prefix: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    key_column: int = 0,
    consequential: set[tuple[str, str]] | None = None,
    skip_columns: set[int] | None = None,
    scored_bindings: set[tuple[str, str]] | None = None,
    value_aliases: Mapping[tuple[str, str], Sequence[str]] | None = None,
) -> list[dict[str, Any]]:
    consequential = consequential or set()
    skip_columns = skip_columns or set()
    value_aliases = value_aliases or {}
    key_order = [str(row[key_column]) for row in rows]
    leaves: list[dict[str, Any]] = [
        leaf(
            f"{prefix}.schema",
            "The region preserves the source field schema in order: " + ", ".join(str(header) for header in headers) + ".",
            claim_type="structure",
            evidence_policy={"type": "ordered_tokens", "tokens": [[str(header)] for header in headers]},
        ),
        leaf(
            f"{prefix}.row-order",
            "The source row order is recoverable as: " + " -> ".join(key_order) + ".",
            claim_type="ordered_record",
            evidence_policy={"type": "ordered_tokens", "tokens": [[key] for key in key_order]},
        ),
    ]
    for row in rows:
        key = str(row[key_column])
        key_slug = slugify(key)
        for column_index, value in enumerate(row):
            if column_index == key_column or column_index in skip_columns:
                continue
            header = str(headers[column_index])
            if scored_bindings is not None and (key, header) not in scored_bindings:
                continue
            leaves.append(
                leaf(
                    f"{prefix}.{key_slug}.{slugify(header)}",
                    f"For {key}, {header} is {value}.",
                    harm=2 if (key, header) in consequential else 1,
                    claim_type="table_binding",
                    evidence_policy={
                        "type": "table_binding",
                        "row": _term_alternatives(key),
                        "column": _term_alternatives(header),
                        "value": list(
                            dict.fromkeys(
                                [
                                    *_term_alternatives(str(value)),
                                    *(
                                        alternative
                                        for alias in value_aliases.get((key, header), ())
                                        for alternative in _term_alternatives(str(alias))
                                    ),
                                ]
                            )
                        ),
                    },
                )
            )
    return leaves


def make_scan(
    title: str,
    lines: Sequence[str],
    *,
    width: int = 1300,
    height: int = 760,
    seed: int = 1,
    marks: Sequence[tuple[int, int, str]] = (),
) -> Image.Image:
    """Create a deterministic, readable scanned-form region with paper texture."""
    rng = random.Random(seed)
    image = Image.new("L", (width, height), 245)
    pixels = image.load()
    for _ in range(width * height // 35):
        px = rng.randrange(width)
        py = rng.randrange(height)
        pixels[px, py] = rng.randrange(225, 250)
    image = image.filter(ImageFilter.GaussianBlur(0.25))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    bold = ImageFont.load_default(size=21)
    draw.text((45, 32), title, font=bold, fill=25)
    draw.line((45, 68, width - 45, 68), fill=80, width=2)
    y = 95
    for line in lines:
        if draw.textlength(line, font=font) > width - 110:
            raise ValueError(f"Scanned-form line exceeds image width: {line!r}")
        if y + 30 > height - 24:
            raise ValueError(f"Scanned-form lines exceed image height near: {line!r}")
        draw.text((55, y), line, font=font, fill=35)
        y += 33
    for x, y, mark in marks:
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"Scanned-form mark is outside the image: {(x, y, mark)!r}")
        if mark == "check":
            draw.line((x, y + 8, x + 8, y + 18), fill=25, width=4)
            draw.line((x + 8, y + 18, x + 28, y - 5), fill=25, width=4)
        elif mark == "strike":
            draw.line((x, y, x + 220, y - 4), fill=35, width=3)
        else:
            draw.text((x, y), mark, font=font, fill=25)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    return image.convert("RGB")


def image_reader(image: Image.Image) -> ImageReader:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return ImageReader(buffer)


@dataclass
class CaseBuilder:
    output_root: Path
    case_id: str
    title: str
    family: str
    tags: list[str]
    page_count: int
    purpose: str
    source_modality: str
    document_ref: str = ""
    metadata_date: str = "D:20260701090000+00'00'"
    canvas: Canvas = field(init=False)
    case_dir: Path = field(init=False)
    pdf_path: Path = field(init=False)
    page_number: int = field(default=0, init=False)
    page_size: tuple[float, float] = field(default=PORTRAIT, init=False)
    gold_parts: list[str] = field(default_factory=list, init=False)
    regions: list[dict[str, Any]] = field(default_factory=list, init=False)
    page_titles: dict[int, str] = field(default_factory=dict, init=False)
    gold_headings: dict[int, str] = field(default_factory=dict, init=False)
    page_modalities: dict[int, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.output_root = self.output_root.resolve()
        try:
            self.output_root.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise ValueError(f"Output root must stay inside the repository: {self.output_root}") from exc
        self.case_dir = self.output_root / "cases" / self.case_id
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_path = self.case_dir / "source.pdf"
        self.canvas = Canvas(str(self.pdf_path), pagesize=PORTRAIT, invariant=1, pageCompression=1)
        self.canvas.setTitle(self.title)
        self.canvas.setAuthor("Document Control")
        self.canvas.setCreator("Office document export")
        self.canvas.setProducer("Enterprise Document Services")
        self.canvas.setDateFormatter(lambda *_: self.metadata_date)

    @property
    def width(self) -> float:
        return self.page_size[0]

    @property
    def height(self) -> float:
        return self.page_size[1]

    def new_page(
        self,
        title: str,
        *,
        subtitle: str = "",
        page_size: tuple[float, float] = PORTRAIT,
        section_code: str = "",
    ) -> Canvas:
        if self.page_number:
            self.canvas.showPage()
        self.page_number += 1
        self.page_size = page_size
        self.page_titles[self.page_number] = title
        self.canvas.setPageSize(page_size)
        self.canvas.setFillColor(PAPER)
        self.canvas.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canvas.setFillColor(MUTED)
        self.canvas.setFont("DocSans-Bold", 7.2)
        self.canvas.drawString(42, self.height - 31, self.family.upper())
        if section_code:
            self.canvas.drawRightString(self.width - 42, self.height - 31, section_code)
        self.canvas.setFillColor(INK)
        self.canvas.setFont("DocSans-Bold", 18)
        self.canvas.drawString(42, self.height - 62, title)
        if subtitle:
            self.canvas.setFont("DocSans", 8)
            self.canvas.setFillColor(MUTED)
            self.canvas.drawString(42, self.height - 78, subtitle)
        self.canvas.setStrokeColor(RULE)
        self.canvas.setLineWidth(0.6)
        self.canvas.line(42, self.height - 88, self.width - 42, self.height - 88)
        self.canvas.setFont("DocSans", 6.8)
        self.canvas.setFillColor(MUTED)
        footer_ref = self.document_ref or f"{self.family.title()} · controlled copy"
        self.canvas.drawString(42, 24, footer_ref)
        self.canvas.drawRightString(self.width - 42, 24, f"{self.page_number} / {self.page_count}")
        return self.canvas

    def add_gold(self, heading: str, body: str) -> None:
        self.gold_parts.append(f"## {heading}\n\n{body.strip()}\n")
        self.gold_headings[self.page_number] = heading

    def set_page_modalities(
        self,
        *,
        native_pages: Sequence[int],
        full_raster_pages: Sequence[int],
        mixed_pages: Sequence[int],
    ) -> None:
        groups = {
            "native_text": list(native_pages),
            "raster": list(full_raster_pages),
            "mixed": list(mixed_pages),
        }
        seen: dict[int, str] = {}
        for modality, pages in groups.items():
            for page in pages:
                if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= self.page_count:
                    raise ValueError(f"{self.case_id}: invalid {modality} page {page!r}")
                if page in seen:
                    raise ValueError(f"{self.case_id}: page {page} appears in both {seen[page]} and {modality}")
                seen[page] = modality
        expected = set(range(1, self.page_count + 1))
        missing = sorted(expected - set(seen))
        if missing:
            raise ValueError(f"{self.case_id}: modality map omits page(s) {missing}")
        self.page_modalities = seen

    @staticmethod
    def _primary_axis(kind: str) -> str:
        return {
            "text": "precise_recall",
            "table": "table_reconstruction",
            "chart": "chart_diagram_spatial",
            "diagram": "chart_diagram_spatial",
            "form": "form_state",
            "image": "image_description",
            "structure": "structure_reconstruction",
            "mixed": "mixed_modality_fusion",
        }[kind]

    @staticmethod
    def _closed_world_keys(kind: str, leaves: Sequence[dict[str, Any]]) -> tuple[str, list[str]]:
        if kind == "table":
            keys = [
                str(leaf_item["evidencePolicy"]["row"][0])
                for leaf_item in leaves
                if leaf_item.get("evidencePolicy", {}).get("type") == "table_binding"
                and leaf_item["evidencePolicy"].get("row")
            ]
            scope = "table_rows"
        elif kind == "form":
            keys = [
                str(leaf_item["evidencePolicy"]["label"][0])
                for leaf_item in leaves
                if leaf_item.get("evidencePolicy", {}).get("type") == "form_state"
                and leaf_item["evidencePolicy"].get("label")
            ]
            scope = "form_options"
        elif kind == "diagram":
            keys = [leaf_item["id"] for leaf_item in leaves]
            scope = "edge_set"
        elif kind == "structure":
            keys = [leaf_item["id"] for leaf_item in leaves]
            scope = "structure_children"
        else:
            keys = [leaf_item["canonicalClaimId"] for leaf_item in leaves]
            scope = "region_claims"
        return scope, list(dict.fromkeys(keys)) or [leaf_item["id"] for leaf_item in leaves]

    def _region_modality(self, page: int, kind: str) -> str:
        page_modality = self.page_modalities.get(page, "native_text")
        if page_modality == "raster":
            return "raster"
        if page_modality == "mixed":
            if kind in {"image", "form"}:
                return "raster"
            if kind in {"chart", "diagram"}:
                return "mixed"
            if kind == "mixed":
                return "mixed"
            return "native_text"
        if kind in {"image"}:
            return "raster"
        if kind in {"chart", "diagram"}:
            return "vector_geometry"
        return "native_text"

    def add_region(
        self,
        region_id: str,
        label: str,
        kind: str,
        leaves: Sequence[dict[str, Any]],
        *,
        page: int | None = None,
        pages: Sequence[int] | None = None,
        budget: int = 1,
        closed_world: bool | dict[str, Any] = False,
        modality: str | None = None,
        unique_evidence: bool = True,
        primary_axis: str | None = None,
        secondary_axes: Sequence[str] = (),
        text_only_recoverable: bool | None = None,
        gold_section: str | None = None,
        source_anchors: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        anchor_pages = list(pages) if pages is not None else [page or self.page_number]
        if not anchor_pages:
            raise ValueError(f"{self.case_id}: region {region_id} has no source page")
        primary_page = anchor_pages[0]
        region_modality = modality or self._region_modality(primary_page, kind)
        if source_anchors is None:
            source_anchors = [
                {
                    "page": source_page,
                    "layer": (
                        region_modality
                        if len(anchor_pages) == 1 and modality is not None
                        else self._region_modality(source_page, kind)
                    ),
                    "sectionPath": [
                        self.title,
                        self.page_titles.get(source_page, f"Page {source_page}"),
                    ],
                }
                for source_page in anchor_pages
            ]
        axes = list(dict.fromkeys(secondary_axes))
        if len(anchor_pages) > 1 and "cross_page_join" not in axes and (primary_axis or self._primary_axis(kind)) != "cross_page_join":
            axes.append("cross_page_join")
        if region_modality == "mixed" and "mixed_modality_fusion" not in axes and (primary_axis or self._primary_axis(kind)) != "mixed_modality_fusion":
            axes.append("mixed_modality_fusion")
        if region_modality == "raster" and "low_quality_scan" not in axes and (primary_axis or self._primary_axis(kind)) != "low_quality_scan":
            axes.append("low_quality_scan")
        closed_world_value: dict[str, Any] | None
        if isinstance(closed_world, dict):
            closed_world_value = closed_world
        elif closed_world:
            scope, keys = self._closed_world_keys(kind, leaves)
            closed_world_value = {"scope": scope, "keys": keys}
        else:
            closed_world_value = None
        self.regions.append(
            {
                "id": region_id,
                "label": label,
                "sourceAnchors": list(source_anchors),
                "goldSection": gold_section or self.gold_headings.get(primary_page, self.page_titles.get(primary_page, label)),
                "_goldSectionExplicit": gold_section is not None,
                "kind": kind,
                "modality": region_modality,
                "uniqueEvidence": unique_evidence,
                "primaryAxis": primary_axis or self._primary_axis(kind),
                "secondaryAxes": axes,
                "textOnlyRecoverable": (
                    text_only_recoverable
                    if text_only_recoverable is not None
                    else region_modality == "native_text" and kind in {"text", "table", "structure"}
                ),
                "budget": budget,
                "leaves": list(leaves),
                **({"closedWorld": closed_world_value} if closed_world_value is not None else {}),
            }
        )

    def finish(self) -> dict[str, Any]:
        if self.page_number != self.page_count:
            raise ValueError(f"{self.case_id}: expected {self.page_count} pages, generated {self.page_number}")
        self.canvas.save()
        # Doc2MD is a reconstruction benchmark. Regions that require a newly
        # authored cross-record conclusion are diagnostic design notes, not
        # scored source evidence. Long-context capability is measured through
        # exhaustive recovery of the actual distributed records instead.
        self.regions = [
            region
            for region in self.regions
            if not str(region["id"]).startswith("x")
            and region["primaryAxis"] != "cross_page_join"
            and all(leaf["claimType"] != "cross_page_join" for leaf in region["leaves"])
        ]
        self.gold_parts = [
            part.split("\n\nIntegrated reference conclusions:", 1)[0].rstrip() + "\n"
            for part in self.gold_parts
            if not part.startswith("## Cross-page entity lineage synthesis")
        ]
        for region in self.regions:
            primary_page = int(region["sourceAnchors"][0]["page"])
            if not region.pop("_goldSectionExplicit", False) and primary_page in self.gold_headings:
                region["goldSection"] = self.gold_headings[primary_page]
        gold = f"# {self.title}\n\n" + "\n".join(self.gold_parts)
        finalize_fact_regions(self.regions, gold)
        (self.case_dir / "gold.md").write_text(gold, encoding="utf-8")
        (self.case_dir / "facts.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 3,
                    "id": self.case_id,
                    "title": self.title,
                    "family": self.family,
                    "tags": self.tags,
                    "regions": self.regions,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.case_dir / "spec.md").write_text(
            f"# {self.title}\n\n"
            f"Source modality: {self.source_modality}\n\n"
            f"Family: `{self.family}`\n\n"
            f"Purpose: {self.purpose}\n\n"
            "Tags: "
            + ", ".join(f"`{tag}`" for tag in self.tags)
            + "\n",
            encoding="utf-8",
        )
        prefix = self.output_root.relative_to(REPO_ROOT).as_posix()
        base = f"{prefix}/cases/{self.case_id}"
        return {
            "id": self.case_id,
            "title": self.title,
            "family": self.family,
            "tags": self.tags,
            "pages": self.page_count,
            "pdf": f"{base}/source.pdf",
            "gold": f"{base}/gold.md",
            "spec": f"{base}/spec.md",
            "facts": f"{base}/facts.json",
        }
