# URL Shortener (CodeAlpha_UrlShortener)

Fast URL shortener service built with Flask and SQLite.

## Features

- Generates 6-character short alphanumeric codes with MD5 hash prefix and entropy.
- Automatic collision detection and retry loop.
- Instant 302 redirection.
- URL statistics and recent link tracking.
- Clickable links and live frontend updates.

## How to Run

```bash
# From this directory:
source .venv/bin/activate  # or ../.venv/bin/activate
python app.py
```

Access the application at [http://localhost:5005](http://localhost:5005).

## Testing

```bash
pytest test_url_shortener.py -v
```
