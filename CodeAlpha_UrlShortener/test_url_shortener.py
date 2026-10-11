import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def client():
    app_path = Path(__file__).parent / "app.py"
    spec = importlib.util.spec_from_file_location("url_shortener_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    with module.app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"URL Shortener" in response.data


def test_shorten_valid_url(client):
    response = client.post("/api/shorten", json={"long_url": "https://example.com/alpha"})
    assert response.status_code == 201
    data = response.get_json()
    assert "short_code" in data
    assert data["long_url"] == "https://example.com/alpha"
    assert data["short_url"].endswith(data["short_code"])


def test_shorten_url_prepends_https(client):
    response = client.post("/api/shorten", json={"long_url": "example.org/path"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["long_url"] == "https://example.org/path"


def test_shorten_missing_url(client):
    response = client.post("/api/shorten", json={"long_url": ""})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_get_url_info_and_redirect(client):
    res = client.post("/api/shorten", json={"long_url": "https://example.com/target"})
    assert res.status_code == 201
    code = res.get_json()["short_code"]

    info_res = client.get(f"/api/{code}")
    assert info_res.status_code == 200
    assert info_res.get_json()["long_url"] == "https://example.com/target"

    redir_res = client.get(f"/{code}")
    assert redir_res.status_code == 302
    assert redir_res.headers["Location"] == "https://example.com/target"


def test_not_found_endpoints(client):
    assert client.get("/api/not_real_code").status_code == 404
    assert client.get("/not_real_code").status_code == 404


def test_stats(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_urls" in data
    assert "recent" in data
    assert isinstance(data["recent"], list)


def test_repeated_shorten_no_collision_errors(client):
    codes = set()
    for _ in range(5):
        res = client.post("/api/shorten", json={"long_url": "https://example.com/repeated"})
        assert res.status_code == 201
        codes.add(res.get_json()["short_code"])
    assert len(codes) == 5
