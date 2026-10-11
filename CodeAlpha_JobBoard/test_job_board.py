import io
import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def client():
    app_path = Path(__file__).parent / "app.py"
    spec = importlib.util.spec_from_file_location("job_board_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    with module.app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Job Board Platform" in response.data


def test_employers(client):
    res = client.get("/api/employers")
    assert res.status_code == 200
    employers = res.get_json()
    assert len(employers) >= 3

    detail_res = client.get(f"/api/employers/{employers[0]['id']}")
    assert detail_res.status_code == 200
    assert "jobs" in detail_res.get_json()


def test_job_search_and_filters(client):
    all_jobs = client.get("/api/jobs").get_json()
    assert len(all_jobs) >= 5

    search_q = client.get("/api/jobs?q=Python").get_json()
    assert len(search_q) >= 1
    assert any("Python" in j["title"] for j in search_q)

    remote_jobs = client.get("/api/jobs?remote=true").get_json()
    assert all(j["is_remote"] == 1 for j in remote_jobs)

    cats_res = client.get("/api/jobs/categories")
    assert cats_res.status_code == 200
    assert "Full-time" in cats_res.get_json()


def test_job_posting_and_close(client):
    new_job = client.post(
        "/api/jobs",
        json={
            "employer_id": 1,
            "title": "Staff Reliability Engineer",
            "description": "Maintain 99.99% system availability.",
            "location": "Remote",
            "job_type": "Full-time",
            "salary_min": 140000,
            "salary_max": 180000,
            "is_remote": 1,
        },
    )
    assert new_job.status_code == 201
    job_id = new_job.get_json()["id"]

    job_detail = client.get(f"/api/jobs/{job_id}")
    assert job_detail.status_code == 200
    assert job_detail.get_json()["title"] == "Staff Reliability Engineer"

    close_res = client.delete(f"/api/jobs/{job_id}")
    assert close_res.status_code == 200

    assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_candidate_registration_resume_and_application_lifecycle(client):
    import secrets
    test_email = f"jordan_{secrets.token_hex(4)}@test.example"
    cand_res = client.post(
        "/api/candidates/register",
        json={
            "full_name": "Jordan Engineer",
            "email": test_email,
            "phone": "555-4321",
            "cover_letter": "Passionate backend engineer.",
        },
    )
    assert cand_res.status_code == 201
    cand = cand_res.get_json()
    cand_id = cand["id"]

    dup = client.post(
        "/api/candidates/register",
        json={"full_name": "Jordan Duplicate", "email": test_email},
    )
    assert dup.status_code == 409

    resume_data = io.BytesIO(b"Candidate CV Content for Jordan Engineer")
    upload_res = client.post(
        f"/api/candidates/{cand_id}/resume",
        data={"file": (resume_data, "resume.txt")},
        content_type="multipart/form-data",
    )
    assert upload_res.status_code == 200
    filename = upload_res.get_json()["filename"]

    download_res = client.get(f"/uploads/{filename}")
    assert download_res.status_code == 200
    assert b"Candidate CV Content" in download_res.data

    apply_res = client.post(
        "/api/jobs/1/apply",
        json={"candidate_id": cand_id, "cover_letter": "Excited to apply!"},
    )
    assert apply_res.status_code == 201
    app_id = apply_res.get_json()["id"]

    dup_apply = client.post("/api/jobs/1/apply", json={"candidate_id": cand_id})
    assert dup_apply.status_code == 409

    app_detail = client.get(f"/api/applications/{app_id}").get_json()
    assert app_detail["status"] == "applied"
    assert len(app_detail["status_history"]) >= 1

    patch_res = client.patch(
        f"/api/applications/{app_id}/status",
        json={"status": "interview", "changed_by": "recruiter"},
    )
    assert patch_res.status_code == 200

    withdraw_res = client.delete(f"/api/applications/{app_id}")
    assert withdraw_res.status_code == 200


def test_platform_dashboard(client):
    dash_res = client.get("/api/reports/dashboard")
    assert dash_res.status_code == 200
    d = dash_res.get_json()
    assert "total_jobs" in d
    assert "total_applications" in d
    assert "employers_count" in d
