# Job Board Platform (CodeAlpha_JobBoard)

Modern job board and applicant tracking platform built with Flask and SQLite.

## Features

- Search and filter jobs by keyword, employment type, location, remote status, and salary range.
- Employer registration and job posting management.
- Candidate registration with resume file upload (`.pdf`, `.docx`, `.txt`, `.png`, `.jpg`).
- Job application submission with cover letter and duplicate prevention.
- Applicant status pipeline (`applied` → `reviewed` → `interview` → `offer` → `accepted` / `rejected` / `withdrawn`).
- Platform dashboard tracking active jobs, candidate metrics, and status distributions.

## How to Run

```bash
# From this directory:
source .venv/bin/activate
python app.py
```

Access the application at [http://localhost:5004](http://localhost:5004).

## Testing

```bash
pytest test_job_board.py -v
```
