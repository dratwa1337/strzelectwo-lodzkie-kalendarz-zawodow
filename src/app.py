"""
Web application for the shooting competition calendar.

Serves:
    /                – Calendar page (FullCalendar.js)
    /api/events      – JSON feed for FullCalendar
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from extract_table import Competition, parse_competitions

# ── App setup ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "data" / "kalendarz2026.pdf"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates"),
    static_folder=str(Path(__file__).resolve().parent / "static"),
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_competitions() -> tuple[Competition, ...]:
    """Parse competitions once and cache. Returns a tuple (hashable for lru_cache)."""
    try:
        return tuple(parse_competitions(PDF_PATH))
    except Exception:
        logger.exception("Failed to load competitions from %s", PDF_PATH)
        return ()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_filter_options(competitions: list[Competition]) -> dict:
    """Collect unique values for filter dropdowns."""
    organizers: set[str] = set()
    locations: set[str] = set()
    names: set[str] = set()

    for c in competitions:
        if c.organizer:
            organizers.add(c.organizer)
        if c.location:
            locations.add(c.location)
        if c.name:
            names.add(c.name)

    return {
        "organizers": sorted(organizers),
        "locations": sorted(locations),
        "names": sorted(names),
    }


def _competition_to_fc_events(comp: Competition) -> list[dict]:
    """Convert a Competition to one or more FullCalendar event objects.

    Comma-separated dates produce separate single-day events.
    Dash-separated (range) dates produce a single multi-day event.
    """
    if not comp.dates or comp.date_start is None:
        return []

    disc = ", ".join(comp.disciplines) if comp.disciplines else ""
    weapon = ", ".join(comp.weapon_types) if comp.weapon_types else ""

    # Color coding by competition type
    color = "#2563eb"  # default blue
    name_lower = comp.name.lower()
    if "puchar" in name_lower:
        color = "#dc2626"  # red for cups
    elif "piro" in name_lower:
        color = "#f97316"  # orange for PiRO GP
    elif "mistrzostwa" in name_lower:
        color = "#059669"  # green for championships

    base = {
        "title": comp.organizer or "Organizator nieznany",
        "allDay": True,
        "color": color,
        "extendedProps": {
            "organizer": comp.organizer,
            "location": comp.location,
            "disciplines": disc,
            "weaponTypes": weapon,
            "result": comp.result,
            "name": comp.name,
        },
    }

    # Multi-day range ("-" separator) → single spanning event
    if comp.is_multiday_range or len(comp.dates) == 1:
        # FullCalendar all-day end is exclusive, so +1 day
        end = None
        if comp.date_end and comp.date_end != comp.date_start:
            end = (comp.date_end + timedelta(days=1)).isoformat()
        return [{
            **base,
            "start": comp.date_start.isoformat(),
            "end": end,
        }]

    # Separate days ("," separator) → one event per date
    return [{
        **base,
        "start": d.isoformat(),
        "end": None,
    } for d in comp.dates]


# ── Routes ─────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the main calendar page."""
    competitions = _load_competitions()
    filters = _get_filter_options(competitions)
    return render_template("index.html", filters=filters)


@app.route("/api/events")
def api_events():
    """JSON event feed for FullCalendar, with optional query-string filters."""
    competitions = _load_competitions()

    # Apply filters from query string (multi-value)
    organizers = [v.strip() for v in request.args.getlist("organizer") if v.strip()]
    locations = [v.strip() for v in request.args.getlist("location") if v.strip()]
    names = [v.strip() for v in request.args.getlist("name") if v.strip()]
    disciplines = [v.strip() for v in request.args.getlist("discipline") if v.strip()]
    weapons = [v.strip() for v in request.args.getlist("weapon") if v.strip()]

    filtered = competitions
    if organizers:
        filtered = [c for c in filtered if c.organizer in organizers]
    if locations:
        filtered = [c for c in filtered if c.location in locations]
    if names:
        filtered = [c for c in filtered if c.name in names]
    if disciplines:
        filtered = [c for c in filtered if any(d in c.disciplines for d in disciplines)]
    if weapons:
        filtered = [c for c in filtered if any(w in c.weapon_types for w in weapons)]

    events = []
    for comp in filtered:
        events.extend(_competition_to_fc_events(comp))

    return jsonify(events)


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
