# Shooting Competition Calendar – Łódzkie 2026

Web application for browsing the shooting competition calendar for the Łódź Voivodeship. Parses competition data from a PDF published by the WZSS (regional shooting association) and displays it as an interactive calendar with multi-select filtering.

## Project Structure

```
.
├── pyproject.toml              # Project config & dependencies (uv)
├── uv.lock                     # Dependency lockfile
├── .python-version             # Pinned Python 3.9
├── src/
│   ├── extract_table.py        # PDF parsing → Competition objects
│   ├── app.py                  # Flask web application
│   ├── static/
│   │   ├── css/style.css       # Styles
│   │   └── js/calendar.js      # FullCalendar integration & multi-select filters
│   └── templates/
│       └── index.html          # Calendar page (FullCalendar.js)
└── data/
    └── kalendarz2026.pdf       # Source PDF from ŁOZSs
```

## Prerequisites

- Python ≥ 3.9
- [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Start the application
uv run python src/app.py

# 3. Open in browser
open http://localhost:8080
```

## Features

The calendar runs at **http://localhost:8080** and offers:

- 📅 **Interactive calendar** — month and list views powered by FullCalendar.js
- 🔍 **Multi-select filters** — competition type, organizer, location, discipline, weapon type
- 📋 **Event details** — click any event for full information
- 🎨 **Color coding** — blue (club), red (Puchar Woj.), orange (PiRO GP), green (championships)

### API

| Endpoint | Description |
|---|---|
| `GET /` | Calendar page |
| `GET /api/events` | JSON event feed for FullCalendar (supports multi-value filters: `?name=`, `?organizer=`, `?location=`, `?discipline=`, `?weapon=`) |

## Dependencies

| Package | Role |
|---|---|
| [Flask](https://flask.palletsprojects.com/) ≥ 3.1.3 | Web server & JSON API |
| [PyMuPDF](https://pymupdf.readthedocs.io/) ≥ 1.26.5 | PDF table extraction |
| [FullCalendar.js](https://fullcalendar.io/) 6.1.17 | Client-side calendar (CDN) |

## Using as a Library

```python
from src.extract_table import parse_competitions

competitions = parse_competitions("data/kalendarz2026.pdf")
for c in competitions:
    print(c.summary)
```

## Licencja

MIT
