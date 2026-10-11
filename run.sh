#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Virtual environment not found. Setting up .venv..."
    uv venv --python 3.11 "$DIR/.venv"
    uv pip install --python "$PYTHON" "flask>=3.0" "werkzeug>=3.0" pytest requests
fi

target="${1:-help}"

case "$target" in
    "CodeAlpha_EventRegistration"|"event-registration"|"event"|"events")
        echo "Starting Event Registration on http://localhost:5002..."
        cd "$DIR/CodeAlpha_EventRegistration" && exec "$PYTHON" app.py
        ;;
    "CodeAlpha_RestaurantManagement"|"restaurant-management"|"restaurant")
        echo "Starting Restaurant Management on http://localhost:5003..."
        cd "$DIR/CodeAlpha_RestaurantManagement" && exec "$PYTHON" app.py
        ;;
    "CodeAlpha_JobBoard"|"job-board"|"jobs")
        echo "Starting Job Board on http://localhost:5004..."
        cd "$DIR/CodeAlpha_JobBoard" && exec "$PYTHON" app.py
        ;;
    "CodeAlpha_UrlShortener"|"url-shortener"|"shortener"|"url")
        echo "Starting URL Shortener on http://localhost:5005..."
        cd "$DIR/CodeAlpha_UrlShortener" && exec "$PYTHON" app.py
        ;;
    "test"|"tests")
        echo "Running test suite across all projects..."
        exec "$DIR/.venv/bin/pytest" "$DIR"/CodeAlpha_*/test_*.py -v
        ;;
    "all")
        echo "Starting all 4 projects in the background:"
        echo " - CodeAlpha_EventRegistration:    http://localhost:5002"
        echo " - CodeAlpha_RestaurantManagement: http://localhost:5003"
        echo " - CodeAlpha_JobBoard:             http://localhost:5004"
        echo " - CodeAlpha_UrlShortener:         http://localhost:5005"
        trap 'kill $(jobs -p)' EXIT INT TERM
        (cd "$DIR/CodeAlpha_EventRegistration" && "$PYTHON" app.py) &
        (cd "$DIR/CodeAlpha_RestaurantManagement" && "$PYTHON" app.py) &
        (cd "$DIR/CodeAlpha_JobBoard" && "$PYTHON" app.py) &
        (cd "$DIR/CodeAlpha_UrlShortener" && "$PYTHON" app.py) &
        wait
        ;;
    *)
        echo "Usage: ./run.sh [project | test | all]"
        echo ""
        echo "Available projects:"
        echo "  CodeAlpha_EventRegistration     (Port 5002)"
        echo "  CodeAlpha_RestaurantManagement  (Port 5003)"
        echo "  CodeAlpha_JobBoard              (Port 5004)"
        echo "  CodeAlpha_UrlShortener          (Port 5005)"
        echo ""
        echo "Commands:"
        echo "  ./run.sh all                    Run all 4 projects concurrently"
        echo "  ./run.sh test                   Run full automated pytest test suite"
        exit 1
        ;;
esac
