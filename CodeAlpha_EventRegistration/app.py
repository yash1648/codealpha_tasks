#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import os
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=APP_DIR)
DB = os.path.join(APP_DIR, "events.db")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL,
            location TEXT,
            max_attendees INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            user_email TEXT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """)
    cnt = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if cnt == 0:
        conn.executemany(
            "INSERT INTO events (title, description, event_date, location, max_attendees) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    "Python & AI Developers Summit",
                    "Annual conference covering modern Python architectures and LLM application engineering.",
                    "2026-11-15T09:00",
                    "Tech Convention Center, Hall A",
                    50,
                ),
                (
                    "Cloud Native Microservices Workshop",
                    "Hands-on architectural patterns for high-scale distributed backends.",
                    "2026-11-20T14:00",
                    "Online (Zoom)",
                    30,
                ),
                (
                    "Open Source Community Hackathon",
                    "Collaborative 24-hour sprint building developer tools and libraries.",
                    "2026-12-05T10:00",
                    "Innovation Hub, Floor 4",
                    0,
                ),
            ],
        )
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events", methods=["GET"])
def list_events():
    conn = get_db()
    events = conn.execute("""
        SELECT e.*, COUNT(r.id) as registered_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        GROUP BY e.id
        ORDER BY e.event_date ASC
    """).fetchall()
    conn.close()
    return jsonify([dict(e) for e in events])


@app.route("/api/events/<int:event_id>", methods=["GET"])
def event_detail(event_id):
    conn = get_db()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "Event not found"}), 404
    regs = conn.execute(
        "SELECT * FROM registrations WHERE event_id = ? ORDER BY registered_at DESC",
        (event_id,),
    ).fetchall()
    conn.close()
    data = dict(event)
    data["registrations"] = [dict(r) for r in regs]
    data["registered_count"] = len(regs)
    data["spots_left"] = (
        (event["max_attendees"] - len(regs))
        if event["max_attendees"] and event["max_attendees"] > 0
        else None
    )
    return jsonify(data)


@app.route("/api/events", methods=["POST"])
def create_event():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO events (title, description, event_date, location, max_attendees) VALUES (?, ?, ?, ?, ?)",
        (
            title,
            data.get("description", ""),
            data.get("event_date", ""),
            data.get("location", ""),
            int(data.get("max_attendees") or 0),
        ),
    )
    conn.commit()
    event_id = cur.lastrowid
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return jsonify(dict(event)), 201


@app.route("/api/events/<int:event_id>", methods=["DELETE"])
def cancel_event(event_id):
    conn = get_db()
    event = conn.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "Event not found"}), 404
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Event cancelled"}), 200


@app.route("/api/events/<int:event_id>/register", methods=["POST"])
def register(event_id):
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    user_name = data.get("user_name", "").strip()
    user_email = data.get("user_email", "").strip()
    if not user_name or not user_email:
        return jsonify({"error": "Name and email required"}), 400
    conn = get_db()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "Event not found"}), 404
    existing = conn.execute(
        "SELECT id FROM registrations WHERE event_id = ? AND user_email = ?",
        (event_id, user_email),
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "You are already registered"}), 400
    if (
        event["max_attendees"]
        and event["max_attendees"]
        <= conn.execute(
            "SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
    ):
        conn.close()
        return jsonify({"error": "Event is full"}), 400
    cur = conn.execute(
        "INSERT INTO registrations (event_id, user_name, user_email) VALUES (?, ?, ?)",
        (event_id, user_name, user_email),
    )
    conn.commit()
    reg = conn.execute(
        "SELECT * FROM registrations WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return jsonify(dict(reg)), 201


@app.route("/api/events/<int:event_id>/register", methods=["GET"])
def list_registrations(event_id):
    conn = get_db()
    event = conn.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "Event not found"}), 404
    regs = conn.execute(
        "SELECT * FROM registrations WHERE event_id = ? ORDER BY registered_at DESC",
        (event_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in regs])


@app.route("/api/registrations/<int:reg_id>", methods=["DELETE"])
def cancel_registration(reg_id):
    conn = get_db()
    reg = conn.execute(
        "SELECT r.*, e.title as event_title FROM registrations r JOIN events e ON r.event_id = e.id WHERE r.id = ?",
        (reg_id,),
    ).fetchone()
    if not reg:
        conn.close()
        return jsonify({"error": "Registration not found"}), 404
    conn.execute("DELETE FROM registrations WHERE id = ?", (reg_id,))
    conn.commit()
    conn.close()
    return jsonify(
        {"message": f"Registration for '{reg['event_title']}' cancelled"}
    ), 200


@app.route("/api/user/<user_email>", methods=["GET"])
def user_registrations(user_email):
    conn = get_db()
    regs = conn.execute(
        """
        SELECT r.id, r.event_id, r.user_name, r.user_email, r.registered_at,
               e.title as event_title, e.event_date, e.location
        FROM registrations r JOIN events e ON r.event_id = e.id
        WHERE r.user_email = ?
        ORDER BY e.event_date ASC
    """,
        (user_email,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in regs])


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5002)
