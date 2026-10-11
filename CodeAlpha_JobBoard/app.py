#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=APP_DIR)
DB = os.path.join(APP_DIR, "jobs.db")
UPLOAD_FOLDER = os.path.join(APP_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"}


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            contact_phone TEXT,
            company_website TEXT,
            company_description TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            requirements TEXT,
            location TEXT,
            job_type TEXT DEFAULT 'Full-time',
            salary_min REAL,
            salary_max REAL,
            is_remote INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employer_id) REFERENCES employers(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            resume_path TEXT,
            cover_letter TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            status TEXT DEFAULT 'applied',
            cover_letter TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES job_postings(id) ON DELETE CASCADE,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS application_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            changed_by TEXT DEFAULT 'system',
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        )
    """)
    # Seed employers
    cnt = conn.execute("SELECT COUNT(*) FROM employers").fetchone()[0]
    if cnt == 0:
        conn.executemany(
            "INSERT INTO employers (company_name, contact_email, contact_phone, company_website, company_description, is_verified) VALUES (?,?,?,?,?,?)",
            [
                (
                    "TechNova Inc.",
                    "hr@technova.example",
                    "555-0101",
                    "https://technova.example",
                    "Leading software company specializing in cloud solutions.",
                    1,
                ),
                (
                    "GreenLeaf Solutions",
                    "careers@greenleaf.example",
                    "555-0102",
                    "https://greenleaf.example",
                    "Sustainability-focused consulting firm.",
                    1,
                ),
                (
                    "DataMinds AI",
                    "jobs@dataminds.example",
                    "555-0103",
                    "https://dataminds.example",
                    "AI and machine learning research lab.",
                    1,
                ),
            ],
        )
    # Seed sample job postings
    job_cnt = conn.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0]
    if job_cnt == 0:
        conn.executemany(
            """INSERT INTO job_postings (employer_id, title, description, requirements, location, job_type, salary_min, salary_max, is_remote)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    1,
                    "Senior Python Backend Engineer",
                    "Architect and scale microservices and APIs supporting our enterprise cloud platform.",
                    "5+ years Python, Flask/FastAPI, PostgreSQL, Docker, AWS.",
                    "Remote",
                    "Full-time",
                    110000.0,
                    145000.0,
                    1,
                ),
                (
                    1,
                    "Cloud Infrastructure Architect",
                    "Design multi-region Kubernetes clusters and automated CI/CD deployment pipelines.",
                    "Terraform, Kubernetes, Linux systems engineering, CI/CD.",
                    "New York, NY",
                    "Full-time",
                    130000.0,
                    165000.0,
                    0,
                ),
                (
                    2,
                    "Sustainability Data Analyst",
                    "Analyze carbon footprint metrics and environmental impact data for corporate partners.",
                    "SQL, Python data tools, dashboards, presentation skills.",
                    "San Francisco, CA",
                    "Full-time",
                    80000.0,
                    100000.0,
                    1,
                ),
                (
                    3,
                    "Machine Learning Research Scientist",
                    "Train and evaluate foundational transformer architectures and retrieval systems.",
                    "PyTorch, distributed training, LLM fine-tuning, research track record.",
                    "Boston, MA",
                    "Full-time",
                    150000.0,
                    190000.0,
                    1,
                ),
                (
                    3,
                    "AI Engineering Intern",
                    "Collaborate with senior researchers on dataset curation and prompt evaluation tooling.",
                    "Python proficiency, curiosity in AI/ML, CS background.",
                    "Remote",
                    "Internship",
                    40000.0,
                    55000.0,
                    1,
                ),
            ],
        )
    conn.commit()
    conn.close()


init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


# ── EMPLOYERS ──
@app.route("/api/employers", methods=["GET"])
def list_employers():
    conn = get_db()
    employers = conn.execute("SELECT * FROM employers ORDER BY company_name").fetchall()
    conn.close()
    return jsonify([dict(e) for e in employers])


@app.route("/api/employers", methods=["POST"])
def create_employer():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    company_name = data.get("company_name", "").strip()
    email = data.get("contact_email", "").strip()
    if not company_name or not email:
        return jsonify({"error": "Company name and email required"}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO employers (company_name, contact_email, contact_phone, company_website, company_description) VALUES (?, ?, ?, ?, ?)",
            (
                company_name,
                email,
                data.get("contact_phone", ""),
                data.get("company_website", ""),
                data.get("company_description", ""),
            ),
        )
        conn.commit()
        emp = conn.execute(
            "SELECT * FROM employers WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        conn.close()
        return jsonify(dict(emp)), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already registered"}), 409


@app.route("/api/employers/<int:emp_id>", methods=["GET"])
def employer_detail(emp_id):
    conn = get_db()
    emp = conn.execute("SELECT * FROM employers WHERE id = ?", (emp_id,)).fetchone()
    if not emp:
        conn.close()
        return jsonify({"error": "Employer not found"}), 404
    jobs = conn.execute(
        "SELECT * FROM job_postings WHERE employer_id = ? AND status = 'active' ORDER BY created_at DESC",
        (emp_id,),
    ).fetchall()
    conn.close()
    data = dict(emp)
    data["jobs_count"] = len(jobs)
    data["jobs"] = [dict(j) for j in jobs]
    return jsonify(data)


# ── JOB POSTINGS ──
@app.route("/api/jobs", methods=["GET"])
def search_jobs():
    query = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    job_type = request.args.get("type", "").strip()
    remote = request.args.get("remote", "").strip()
    category = request.args.get("category", "").strip()
    salary_min = request.args.get("salary_min", type=float)
    salary_max = request.args.get("salary_max", type=float)

    conn = get_db()
    base = """
        SELECT j.*, e.company_name, e.contact_email
        FROM job_postings j
        JOIN employers e ON j.employer_id = e.id
        WHERE j.status = 'active'
    """
    params = []
    conditions = []
    if query:
        conditions.append(
            "(j.title LIKE ? OR j.description LIKE ? OR e.company_name LIKE ?)"
        )
        like_q = f"%{query}%"
        params.extend([like_q, like_q, like_q])
    if location:
        conditions.append("j.location LIKE ?")
        params.append(f"%{location}%")
    if job_type:
        conditions.append("j.job_type = ?")
        params.append(job_type)
    if remote == "true":
        conditions.append("j.is_remote = 1")
    if category:
        conditions.append(
            "? IS NULL OR j.category = ?"
        ) if False else conditions.append("1=1")  # simplified
    if salary_min is not None:
        conditions.append("(j.salary_max >= ? OR j.salary_max IS NULL)")
        params.append(salary_min)
    if salary_max is not None:
        conditions.append("(j.salary_min <= ? OR j.salary_min IS NULL)")
        params.append(salary_max)

    if conditions:
        base += " AND " + " AND ".join(conditions)

    base += " ORDER BY j.created_at DESC"
    jobs = conn.execute(base, params).fetchall()
    conn.close()
    return jsonify([dict(j) for j in jobs])


@app.route("/api/jobs/categories", methods=["GET"])
def job_categories():
    conn = get_db()
    cats = conn.execute(
        "SELECT DISTINCT job_type FROM job_postings WHERE status = 'active' ORDER BY job_type"
    ).fetchall()
    conn.close()
    return jsonify([c["job_type"] for c in cats])


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def job_detail(job_id):
    conn = get_db()
    job = conn.execute(
        """
        SELECT j.*, e.company_name, e.contact_email, e.company_website, e.company_description as employer_desc, e.is_verified
        FROM job_postings j JOIN employers e ON j.employer_id = e.id
        WHERE j.id = ? AND j.status = 'active'
    """,
        (job_id,),
    ).fetchone()
    if not job:
        conn.close()
        return jsonify({"error": "Job not found"}), 404
    applications_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE job_id = ?", (job_id,)
    ).fetchone()[0]
    conn.close()
    data = dict(job)
    data["applications_count"] = applications_count
    return jsonify(data)


@app.route("/api/jobs", methods=["POST"])
def post_job():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    employer_id = data.get("employer_id")
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    if not employer_id or not title or not description:
        return jsonify({"error": "Employer ID, title, and description required"}), 400
    conn = get_db()
    emp = conn.execute(
        "SELECT id FROM employers WHERE id = ?", (employer_id,)
    ).fetchone()
    if not emp:
        conn.close()
        return jsonify({"error": "Employer not found"}), 404
    cur = conn.execute(
        """
        INSERT INTO job_postings (employer_id, title, description, requirements, location, job_type, salary_min, salary_max, is_remote)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            employer_id,
            title,
            description,
            data.get("requirements", ""),
            data.get("location", ""),
            data.get("job_type", "Full-time"),
            data.get("salary_min"),
            data.get("salary_max"),
            1 if data.get("is_remote") else 0,
        ),
    )
    conn.commit()
    job = conn.execute(
        "SELECT * FROM job_postings WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return jsonify(dict(job)), 201


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def remove_job(job_id):
    conn = get_db()
    job = conn.execute("SELECT id FROM job_postings WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        return jsonify({"error": "Job not found"}), 404
    conn.execute("UPDATE job_postings SET status = 'closed' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Job closed"})


# ── CANDIDATES ──
@app.route("/api/candidates", methods=["GET"])
def list_candidates():
    conn = get_db()
    candidates = conn.execute(
        "SELECT id, full_name, email, phone, created_at FROM candidates ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(c) for c in candidates])


@app.route("/api/candidates/register", methods=["POST"])
def register_candidate():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    if not name or not email:
        return jsonify({"error": "Name and email required"}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO candidates (full_name, email, phone, cover_letter) VALUES (?, ?, ?, ?)",
            (name, email, data.get("phone", ""), data.get("cover_letter", "")),
        )
        conn.commit()
        cand = conn.execute(
            "SELECT * FROM candidates WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        conn.close()
        return jsonify(dict(cand)), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already registered"}), 409


@app.route("/api/candidates/<int:cand_id>", methods=["GET"])
def candidate_detail(cand_id):
    conn = get_db()
    cand = conn.execute("SELECT * FROM candidates WHERE id = ?", (cand_id,)).fetchone()
    if not cand:
        conn.close()
        return jsonify({"error": "Candidate not found"}), 404
    apps = conn.execute(
        """
        SELECT a.*, j.title as job_title, e.company_name, j.location
        FROM applications a
        JOIN job_postings j ON a.job_id = j.id
        JOIN employers e ON j.employer_id = e.id
        WHERE a.candidate_id = ?
        ORDER BY a.applied_at DESC
    """,
        (cand_id,),
    ).fetchall()
    conn.close()
    data = dict(cand)
    data["applications"] = [dict(a) for a in apps]
    return jsonify(data)


# ── RESUME UPLOAD ──
@app.route("/api/candidates/<int:cand_id>/resume", methods=["POST"])
def upload_resume(cand_id):
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify(
            {
                "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }
        ), 400
    conn = get_db()
    cand = conn.execute("SELECT id FROM candidates WHERE id = ?", (cand_id,)).fetchone()
    if not cand:
        conn.close()
        return jsonify({"error": "Candidate not found"}), 404
    ext = (
        (file.filename or "").rsplit(".", 1)[1].lower()
        if "." in (file.filename or "")
        else "bin"
    )
    filename = f"resume_{cand_id}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    conn.execute(
        "UPDATE candidates SET resume_path = ? WHERE id = ?", (filename, cand_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Resume uploaded", "filename": filename})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/candidates/<int:cand_id>/resume", methods=["DELETE"])
def remove_resume(cand_id):
    conn = get_db()
    cand = conn.execute(
        "SELECT resume_path FROM candidates WHERE id = ?", (cand_id,)
    ).fetchone()
    if cand and cand["resume_path"]:
        fp = os.path.join(app.config["UPLOAD_FOLDER"], cand["resume_path"])
        if os.path.exists(fp):
            os.remove(fp)
        conn.execute(
            "UPDATE candidates SET resume_path = NULL WHERE id = ?", (cand_id,)
        )
        conn.commit()
    conn.close()
    return jsonify({"message": "Resume removed"})


# ── APPLICATIONS ──
@app.route("/api/jobs/<int:job_id>/apply", methods=["POST"])
def apply_job(job_id):
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    candidate_id = data.get("candidate_id")
    cover_letter = data.get("cover_letter", "").strip()
    if not candidate_id:
        return jsonify({"error": "Candidate ID required"}), 400
    conn = get_db()
    job = conn.execute(
        "SELECT id FROM job_postings WHERE id = ? AND status = 'active'", (job_id,)
    ).fetchone()
    if not job:
        conn.close()
        return jsonify({"error": "Job not found or closed"}), 404
    cand = conn.execute(
        "SELECT id FROM candidates WHERE id = ?", (candidate_id,)
    ).fetchone()
    if not cand:
        conn.close()
        return jsonify({"error": "Candidate not found"}), 404
    existing = conn.execute(
        "SELECT id FROM applications WHERE job_id = ? AND candidate_id = ?",
        (job_id, candidate_id),
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "You have already applied to this job"}), 409
    cur = conn.execute(
        "INSERT INTO applications (job_id, candidate_id, cover_letter) VALUES (?, ?, ?)",
        (job_id, candidate_id, cover_letter),
    )
    conn.execute(
        "UPDATE applications SET applied_at = ?, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), datetime.now().isoformat(), cur.lastrowid),
    )
    conn.execute(
        "INSERT INTO application_status_history (application_id, to_status) VALUES (?, 'applied')",
        (cur.lastrowid,),
    )
    conn.commit()
    app_row = conn.execute(
        "SELECT * FROM applications WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return jsonify(dict(app_row)), 201


@app.route("/api/applications", methods=["GET"])
def list_applications():
    job_id = request.args.get("job_id", type=int)
    candidate_id = request.args.get("candidate_id", type=int)
    status = request.args.get("status", "").strip()
    conn = get_db()
    base = """
        SELECT a.*, j.title as job_title, j.location, j.job_type, j.salary_min, j.salary_max,
               e.company_name, c.full_name as candidate_name, c.email as candidate_email, c.resume_path
        FROM applications a
        JOIN job_postings j ON a.job_id = j.id
        JOIN employers e ON j.employer_id = e.id
        JOIN candidates c ON a.candidate_id = c.id
    """
    params = []
    conditions = []
    if job_id:
        conditions.append("a.job_id = ?")
        params.append(job_id)
    if candidate_id:
        conditions.append("a.candidate_id = ?")
        params.append(candidate_id)
    if status:
        conditions.append("a.status = ?")
        params.append(status)
    if conditions:
        base += " WHERE " + " AND ".join(conditions)
    base += " ORDER BY a.applied_at DESC"
    apps = conn.execute(base, params).fetchall()
    conn.close()
    return jsonify([dict(a) for a in apps])


@app.route("/api/applications/<int:app_id>", methods=["GET"])
def application_detail(app_id):
    conn = get_db()
    app = conn.execute(
        """
        SELECT a.*, j.title as job_title, j.description as job_desc, j.location, j.job_type, e.company_name,
               c.full_name, c.email, c.phone, c.resume_path
        FROM applications a
        JOIN job_postings j ON a.job_id = j.id
        JOIN employers e ON j.employer_id = e.id
        JOIN candidates c ON a.candidate_id = c.id
        WHERE a.id = ?
    """,
        (app_id,),
    ).fetchone()
    if not app:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    history = conn.execute(
        "SELECT * FROM application_status_history WHERE application_id = ? ORDER BY changed_at DESC",
        (app_id,),
    ).fetchall()
    conn.close()
    data = dict(app)
    data["status_history"] = [dict(h) for h in history]
    return jsonify(data)


@app.route("/api/applications/<int:app_id>/status", methods=["PATCH"])
def update_application_status(app_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    changed_by = data.get("changed_by", "system").strip() or "system"
    valid = [
        "applied",
        "reviewed",
        "interview",
        "offer",
        "accepted",
        "rejected",
        "withdrawn",
    ]
    if new_status not in valid:
        return jsonify({"error": f"Status must be: {', '.join(valid)}"}), 400
    conn = get_db()
    app = conn.execute(
        "SELECT id, status FROM applications WHERE id = ?", (app_id,)
    ).fetchone()
    if not app:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if app["status"] == new_status:
        conn.close()
        return jsonify({"message": "Status unchanged"})
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, datetime.now().isoformat(), app_id),
    )
    conn.execute(
        "INSERT INTO application_status_history (application_id, from_status, to_status, changed_by) VALUES (?, ?, ?, ?)",
        (app_id, app["status"], new_status, changed_by),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": f"Status updated to '{new_status}'"})


@app.route("/api/applications/<int:app_id>", methods=["DELETE"])
def withdraw_application(app_id):
    conn = get_db()
    app = conn.execute(
        "SELECT id, status FROM applications WHERE id = ?", (app_id,)
    ).fetchone()
    if not app:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if app["status"] in ("accepted",):
        conn.close()
        return jsonify({"error": "Cannot withdraw an accepted application"}), 400
    conn.execute(
        "UPDATE applications SET status = 'withdrawn', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), app_id),
    )
    conn.execute(
        "INSERT INTO application_status_history (application_id, from_status, to_status, changed_by) VALUES (?, ?, 'withdrawn', 'candidate')",
        (app_id, app["status"]),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Application withdrawn"})


# ── REPORTS ──
@app.route("/api/reports/dashboard", methods=["GET"])
def dashboard():
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    total_jobs = conn.execute(
        "SELECT COUNT(*) FROM job_postings WHERE status = 'active'"
    ).fetchone()[0]
    total_applications = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    new_apps_today = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE date(applied_at) = ?", (today,)
    ).fetchone()[0]
    active_candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    employers = conn.execute("SELECT COUNT(*) FROM employers").fetchone()[0]
    # Applications by status
    status_breakdown = conn.execute("""
        SELECT status, COUNT(*) as count FROM applications GROUP BY status
    """).fetchall()
    status_breakdown = {r["status"]: r["count"] for r in status_breakdown}
    # Top jobs by applications
    top_jobs = conn.execute("""
        SELECT j.id, j.title, e.company_name, COUNT(a.id) as app_count
        FROM job_postings j JOIN employers e ON j.employer_id = e.id
        LEFT JOIN applications a ON j.id = a.job_id
        GROUP BY j.id ORDER BY app_count DESC LIMIT 5
    """).fetchall()
    conn.close()
    return jsonify(
        {
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "new_applications_today": new_apps_today,
            "active_candidates": active_candidates,
            "employers_count": employers,
            "applications_by_status": status_breakdown,
            "top_jobs": [dict(j) for j in top_jobs],
        }
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5004)
