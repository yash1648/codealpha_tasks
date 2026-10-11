#!/usr/bin/env python3
from flask import Flask, request, jsonify, redirect, render_template
import sqlite3
import os
import string
import random
import hashlib
import secrets

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=APP_DIR)
DB = os.path.join(APP_DIR, "url_shortener.db")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            long_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def generate_short_code(url, length=6):
    entropy = secrets.token_hex(4)
    hash_hex = hashlib.md5(f"{url}_{entropy}".encode()).hexdigest()[:4]
    random_part = "".join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )
    return (hash_hex + random_part)[:length].lower()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    long_url = data.get("long_url", "").strip()
    if not long_url:
        return jsonify({"error": "URL is required"}), 400
    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url
    conn = get_db()
    short_code = None
    for _ in range(5):
        code_candidate = generate_short_code(long_url)
        try:
            conn.execute(
                "INSERT INTO urls (short_code, long_url) VALUES (?, ?)",
                (code_candidate, long_url),
            )
            conn.commit()
            short_code = code_candidate
            break
        except sqlite3.IntegrityError:
            continue
    conn.close()
    if not short_code:
        return jsonify({"error": "Failed to generate unique code"}), 500
    return jsonify(
        {
            "short_code": short_code,
            "short_url": request.host_url + short_code,
            "long_url": long_url,
        }
    ), 201


@app.route("/api/<short_code>", methods=["GET"])
def get_url(short_code):
    conn = get_db()
    row = conn.execute(
        "SELECT long_url, created_at FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()
    conn.close()
    if row:
        return jsonify(
            {
                "long_url": row["long_url"],
                "created_at": row["created_at"],
                "short_code": short_code,
            }
        )
    return jsonify({"error": "Not found"}), 404


@app.route("/<short_code>", methods=["GET"])
def redirect_url(short_code):
    conn = get_db()
    row = conn.execute(
        "SELECT long_url FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()
    conn.close()
    if row:
        return redirect(row["long_url"], code=302)
    return jsonify({"error": "Short URL not found"}), 404


@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
    recent = conn.execute(
        "SELECT short_code, long_url, created_at FROM urls ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return jsonify({"total_urls": total, "recent": [dict(r) for r in recent]})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5005)
