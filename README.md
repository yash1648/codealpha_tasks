# Internship Projects (CodeAlpha)

A collection of 4 modular, runnable web applications built with Python (Flask) and SQLite.

## Projects Overview

| Project                                                                                                         | Port   | Description                                                                      | Tech Stack               |
| --------------------------------------------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------- | ------------------------ |
| [`CodeAlpha_EventRegistration`](file:///home/grim/Work/internship/code-alpha/CodeAlpha_EventRegistration)       | `5002` | Event schedule, capacity tracking, attendee registration & cancel                | Flask, SQLite, HTML5/CSS |
| [`CodeAlpha_RestaurantManagement`](file:///home/grim/Work/internship/code-alpha/CodeAlpha_RestaurantManagement) | `5003` | POS orders, table statuses, conflict-free reservations, inventory & reports      | Flask, SQLite, HTML5/CSS |
| [`CodeAlpha_JobBoard`](file:///home/grim/Work/internship/code-alpha/CodeAlpha_JobBoard)                         | `5004` | Job search & posting, candidate profiles, resume upload/view, applicant tracking | Flask, SQLite, HTML5/CSS |
| [`CodeAlpha_UrlShortener`](file:///home/grim/Work/internship/code-alpha/CodeAlpha_UrlShortener)                 | `5005` | URL shortening with collision retry, 302 redirects, clickable links & stats      | Flask, SQLite, HTML5/CSS |

---

## Quick Start

### 1. Environment & Setup

A shared virtual environment is configured at `.venv` (with symlinks in each project directory):

```bash
# Activate virtual environment
source .venv/bin/activate
```

Dependencies:

- `Flask>=3.0`
- `Werkzeug>=3.0`
- `pytest>=8.0`

### 2. Running Projects

You can run individual projects or all of them together:

#### Option A: Using the Unified Runner Script

```bash
# Run any single project
./run.sh CodeAlpha_EventRegistration      # Runs on http://localhost:5002
./run.sh CodeAlpha_RestaurantManagement   # Runs on http://localhost:5003
./run.sh CodeAlpha_JobBoard               # Runs on http://localhost:5004
./run.sh CodeAlpha_UrlShortener           # Runs on http://localhost:5005

# Run all 4 projects simultaneously in background
./run.sh all

# Run full automated test suite
./run.sh test
```

#### Option B: Running Directly

```bash
# Event Registration
cd CodeAlpha_EventRegistration && python app.py

# Restaurant Management
cd CodeAlpha_RestaurantManagement && python app.py

# Job Board
cd CodeAlpha_JobBoard && python app.py

# URL Shortener
cd CodeAlpha_UrlShortener && python app.py
```

---

## Testing & Verification

Run the automated test suite across all 4 applications:

```bash
./run.sh test
```

or:

```bash
.venv/bin/pytest CodeAlpha_*/test_*.py -v
```

All 25 automated tests pass with 100% test coverage over key API endpoints, validation logic, capacity bounds, and database integrity.
