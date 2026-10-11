# Event Registration System (CodeAlpha_EventRegistration)

Full-featured event registration and attendee tracking platform built with Flask and SQLite.

## Features

- List upcoming events with dynamic spot countdowns (`spots_left`).
- Create new events with location, date, and attendee capacity limits.
- Register attendees with automatic duplicate email prevention.
- Enforce capacity bounds with strict "Event is full" validation.
- Cancel registrations and dynamically refresh attendee lists.
- Query registrations by user email.

## How to Run

```bash
# From this directory:
source .venv/bin/activate
python app.py
```

Access the application at [http://localhost:5002](http://localhost:5002).

## Testing

```bash
pytest test_event_registration.py -v
```
