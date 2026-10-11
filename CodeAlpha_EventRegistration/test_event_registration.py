import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def client():
    app_path = Path(__file__).parent / "app.py"
    spec = importlib.util.spec_from_file_location("event_registration_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    with module.app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Event Registration" in response.data


def test_list_events(client):
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.get_json()
    assert isinstance(events, list)
    assert len(events) > 0
    first = events[0]
    assert "registered_count" in first
    assert isinstance(first["registered_count"], int)


def test_create_and_detail_event(client):
    create_res = client.post(
        "/api/events",
        json={
            "title": "Automated Test Summit",
            "description": "Integration testing event",
            "event_date": "2026-11-30T10:00",
            "location": "Virtual Room 1",
            "max_attendees": 2,
        },
    )
    assert create_res.status_code == 201
    event = create_res.get_json()
    event_id = event["id"]

    detail_res = client.get(f"/api/events/{event_id}")
    assert detail_res.status_code == 200
    detail = detail_res.get_json()
    assert detail["title"] == "Automated Test Summit"
    assert detail["registered_count"] == 0
    assert detail["spots_left"] == 2


def test_create_event_validation(client):
    res = client.post("/api/events", json={"title": " "})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_register_flow_and_capacity(client):
    import secrets
    u1 = f"alice_{secrets.token_hex(3)}@test.example"
    u2 = f"bob_{secrets.token_hex(3)}@test.example"
    create_res = client.post(
        "/api/events",
        json={
            "title": "Capacity Bound Workshop",
            "event_date": "2026-12-01T15:00",
            "max_attendees": 1,
        },
    )
    event_id = create_res.get_json()["id"]

    reg1 = client.post(
        f"/api/events/{event_id}/register",
        json={"user_name": "Alice Tester", "user_email": u1},
    )
    assert reg1.status_code == 201
    reg1_id = reg1.get_json()["id"]

    dup = client.post(
        f"/api/events/{event_id}/register",
        json={"user_name": "Alice Tester", "user_email": u1},
    )
    assert dup.status_code == 400
    assert "already registered" in dup.get_json()["error"]

    full = client.post(
        f"/api/events/{event_id}/register",
        json={"user_name": "Bob Tester", "user_email": u2},
    )
    assert full.status_code == 400
    assert "Event is full" in full.get_json()["error"]

    user_events = client.get(f"/api/user/{u1}")
    assert user_events.status_code == 200
    assert any(r["event_id"] == event_id for r in user_events.get_json())

    del_reg = client.delete(f"/api/registrations/{reg1_id}")
    assert del_reg.status_code == 200

    detail_after = client.get(f"/api/events/{event_id}").get_json()
    assert detail_after["registered_count"] == 0
    assert detail_after["spots_left"] == 1


def test_cancel_event(client):
    create_res = client.post(
        "/api/events",
        json={"title": "Temporary Event", "event_date": "2026-12-10T12:00"},
    )
    event_id = create_res.get_json()["id"]

    del_res = client.delete(f"/api/events/{event_id}")
    assert del_res.status_code == 200

    assert client.get(f"/api/events/{event_id}").status_code == 404
