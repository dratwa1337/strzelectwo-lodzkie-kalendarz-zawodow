"""
Extract shooting competition calendar from the ŁOZSs PDF.

Reads data/kalendarz2026.pdf, parses the table spanning multiple pages,
and produces a list of Competition objects with proper Python dates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

# ── Constants ──────────────────────────────────────────────────────────────────

YEAR = 2026

# Polish month names → month numbers
MONTH_NAMES: dict[str, int] = {
    "styczeń": 1,
    "luty": 2,
    "marzec": 3,
    "kwiecień": 4,
    "maj": 5,
    "czerwiec": 6,
    "lipiec": 7,
    "sierpień": 8,
    "wrzesień": 9,
    "październik": 10,
    "listopad": 11,
    "grudzień": 12,
}

# Flat column names we assign after extraction (the PDF header spans 2 rows)
COLUMNS = [
    "termin",
    "nazwa",
    "pistolet",
    "karabin",
    "strzelba",
    "pneumatyczna",
    "palna",
    "miejsce",
    "organizator",
    "wynik",
]


# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class Competition:
    """A single competition entry from the calendar."""

    dates: list[date] = field(default_factory=list)
    name: str = ""
    disciplines: list[str] = field(default_factory=list)
    weapon_types: list[str] = field(default_factory=list)
    location: str = ""
    organizer: str = ""
    result: str = ""
    is_multiday_range: bool = False

    @property
    def date_start(self) -> date | None:
        return min(self.dates) if self.dates else None

    @property
    def date_end(self) -> date | None:
        return max(self.dates) if self.dates else None

    @property
    def summary(self) -> str:
        disc = ", ".join(self.disciplines) if self.disciplines else "—"
        weapon = ", ".join(self.weapon_types) if self.weapon_types else "—"
        return f"{self.name} | {disc} | {weapon} | {self.location} ({self.organizer})"


# ── Date parsing ───────────────────────────────────────────────────────────────


def parse_dates(raw: str, year: int = YEAR) -> list[date]:
    """
    Parse the various date formats found in the PDF into date objects.

    Each format already encodes the month in the string itself (DD.MM),
    so no external month context is required.

    Examples:
        '10.01'         → [date(2026, 1, 10)]
        '8,11.01'       → [date(2026, 1, 8), date(2026, 1, 11)]
        '10-11.01'      → [date(2026, 1, 10), date(2026, 1, 11)]
        '28.02,1.03'    → [date(2026, 2, 28), date(2026, 3, 1)]
        '19.21.03'      → [date(2026, 3, 19), date(2026, 3, 21)]  (typo for 19,21)
    """
    raw = raw.strip()
    if not raw:
        return []

    dates: list[date] = []

    # Pattern: "28.02,1.03" – dates spanning two months
    cross_month = re.match(r"^(\d{1,2})\.(\d{2}),(\d{1,2})\.(\d{2})$", raw)
    if cross_month:
        d1, m1, d2, m2 = (int(g) for g in cross_month.groups())
        dates.append(date(year, m1, d1))
        dates.append(date(year, m2, d2))
        return dates

    # Pattern: "19.21.03" – likely a typo for "19,21.03"
    typo_match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2})$", raw)
    if typo_match:
        d1, d2, m = (int(g) for g in typo_match.groups())
        if 1 <= d1 <= 31 and 1 <= d2 <= 31:
            dates.append(date(year, m, d1))
            dates.append(date(year, m, d2))
            return dates

    # Pattern: "10-11.01" – day range in the same month
    range_match = re.match(r"^(\d{1,2})-(\d{1,2})\.(\d{2})$", raw)
    if range_match:
        d_start, d_end, m = (int(g) for g in range_match.groups())
        for d in range(d_start, d_end + 1):
            dates.append(date(year, m, d))
        return dates

    # Pattern: "8,11.01" or "5,8.03" – comma-separated days, same month
    multi_match = re.match(r"^(\d{1,2}),(\d{1,2})\.(\d{2})$", raw)
    if multi_match:
        d1, d2, m = (int(g) for g in multi_match.groups())
        dates.append(date(year, m, d1))
        dates.append(date(year, m, d2))
        return dates

    # Pattern: "10.01" – single date
    single_match = re.match(r"^(\d{1,2})\.(\d{2})$", raw)
    if single_match:
        d, m = (int(g) for g in single_match.groups())
        dates.append(date(year, m, d))
        return dates

    return dates


# ── PDF extraction ─────────────────────────────────────────────────────────────


def extract_raw_rows(pdf_path: str | Path) -> list[list[str]]:
    """
    Open the PDF, find the table on every page, and return all data rows
    concatenated together with flat column names.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    all_rows: list[list[str]] = []
    doc = fitz.open(str(pdf_path))

    for page in doc:
        tables = page.find_tables()
        for table in tables:
            data = table.extract()
            for row in data:
                cleaned = [str(cell or "").strip() for cell in row]
                all_rows.append(cleaned)

    doc.close()
    return all_rows


def _is_month_row(row: list[str]) -> str | None:
    """Return the month name if this row is a month separator, else None."""
    first = row[0].strip().lower() if row[0] else ""
    return first if first in MONTH_NAMES else None


def _is_header_row(row: list[str]) -> bool:
    """Detect the 2-row header that repeats at the top of each page."""
    first = (row[0] or "").lower()
    return "termin" in first or first in ("", "p", "k", "s", "pn", "pal")


def _is_empty_row(row: list[str]) -> bool:
    return all(cell.strip() == "" for cell in row)


def parse_competitions(pdf_path: str | Path) -> list[Competition]:
    """
    Main entry point: read the PDF and return a list of Competition objects.
    """
    raw_rows = extract_raw_rows(pdf_path)
    competitions: list[Competition] = []

    for row in raw_rows:
        # Skip header rows that repeat on each page
        if _is_header_row(row):
            continue

        # Skip empty rows
        if _is_empty_row(row):
            continue

        # Skip month separator rows
        if _is_month_row(row):
            continue

        # Ensure the row has enough columns
        if len(row) < len(COLUMNS):
            row.extend([""] * (len(COLUMNS) - len(row)))

        termin, nazwa, pist, kar, strz, pneu, pal, miejsce, org, wynik = row[
            : len(COLUMNS)
        ]

        # Parse dates
        dates = parse_dates(termin)

        # Dates with "-" are multi-day ranges; "," means separate individual days
        is_multiday_range = bool(re.search(r'\d+-\d+', termin))

        # Build discipline list from 'x' markers
        disciplines: list[str] = []
        if pist.strip().lower() == "x":
            disciplines.append("pistolet")
        if kar.strip().lower() == "x":
            disciplines.append("karabin")
        if strz.strip().lower() == "x":
            disciplines.append("strzelba")

        # Build weapon type list from 'x' markers
        weapon_types: list[str] = []
        if pneu.strip().lower() == "x":
            weapon_types.append("pneumatyczna")
        if pal.strip().lower() == "x":
            weapon_types.append("palna")

        comp = Competition(
            dates=dates,
            name=nazwa.strip(),
            disciplines=disciplines,
            weapon_types=weapon_types,
            location=miejsce.strip(),
            organizer=org.strip(),
            result=wynik.strip(),
            is_multiday_range=is_multiday_range,
        )
        competitions.append(comp)

    return competitions