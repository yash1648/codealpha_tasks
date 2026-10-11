import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def client():
    app_path = Path(__file__).parent / "app.py"
    spec = importlib.util.spec_from_file_location("restaurant_management_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    with module.app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Restaurant Management System" in response.data


def test_menu_endpoints(client):
    menu_res = client.get("/api/menu")
    assert menu_res.status_code == 200
    menu = menu_res.get_json()
    assert len(menu) >= 10

    cat_res = client.get("/api/menu/categories")
    assert cat_res.status_code == 200
    assert "Pizza" in cat_res.get_json()


def test_order_flow_and_items_list(client):
    order_res = client.post(
        "/api/orders",
        json={
            "customer_name": "Test Customer",
            "table_id": 1,
            "items": [{"id": 1, "quantity": 2, "notes": "Extra crispy"}],
        },
    )
    assert order_res.status_code == 201
    order = order_res.get_json()
    order_id = order["id"]
    assert order["total"] > 0
    assert len(order["items"]) == 1
    assert order["items"][0]["item_name"] == "Margherita Pizza"

    orders_list_res = client.get("/api/orders")
    assert orders_list_res.status_code == 200
    orders = orders_list_res.get_json()
    created_order = next(o for o in orders if o["id"] == order_id)
    assert "items" in created_order
    assert len(created_order["items"]) == 1
    assert created_order["items"][0]["item_name"] == "Margherita Pizza"

    patch_res = client.patch(f"/api/orders/{order_id}", json={"status": "completed"})
    assert patch_res.status_code == 200

    table_res = client.get("/api/tables")
    table_1 = next(t for t in table_res.get_json() if t["id"] == 1)
    assert table_1["status"] == "available"


def test_reservations_allow_different_tables_same_time(client):
    import secrets
    date = f"2026-12-{secrets.token_hex(2)}"
    time = "19:00"

    res1 = client.post(
        "/api/reservations",
        json={
            "customer_name": "Party One",
            "table_id": 1,
            "party_size": 2,
            "reservation_date": date,
            "reservation_time": time,
        },
    )
    assert res1.status_code == 201
    r1_id = res1.get_json()["id"]

    res2 = client.post(
        "/api/reservations",
        json={
            "customer_name": "Party Two",
            "table_id": 2,
            "party_size": 2,
            "reservation_date": date,
            "reservation_time": time,
        },
    )
    assert res2.status_code == 201
    r2_id = res2.get_json()["id"]

    conflict = client.post(
        "/api/reservations",
        json={
            "customer_name": "Party Three Conflict",
            "table_id": 1,
            "party_size": 2,
            "reservation_date": date,
            "reservation_time": time,
        },
    )
    assert conflict.status_code == 400
    assert "already booked" in conflict.get_json()["error"]

    client.delete(f"/api/reservations/{r1_id}")
    client.delete(f"/api/reservations/{r2_id}")


def test_inventory_and_reports(client):
    inv_res = client.get("/api/inventory")
    assert inv_res.status_code == 200
    items = inv_res.get_json()
    assert len(items) > 0
    first_item = items[0]

    adj_res = client.patch(f"/api/inventory/{first_item['id']}", json={"delta": 5})
    assert adj_res.status_code == 200

    summary_res = client.get("/api/reports/summary")
    assert summary_res.status_code == 200
    summary = summary_res.get_json()
    assert "total_revenue" in summary
    assert "orders_today" in summary

    daily_sales_res = client.get("/api/reports/daily-sales")
    assert daily_sales_res.status_code == 200
    assert "orders" in daily_sales_res.get_json()
