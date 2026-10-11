#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import secrets
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=APP_DIR)
DB = os.path.join(APP_DIR, "restaurant.db")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL DEFAULT 0,
            category TEXT DEFAULT 'General',
            available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number INTEGER UNIQUE NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 4,
            status TEXT DEFAULT 'available'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            customer_email TEXT,
            party_size INTEGER NOT NULL,
            reservation_date TEXT NOT NULL,
            reservation_time TEXT NOT NULL,
            status TEXT DEFAULT 'confirmed',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            customer_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            total REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            special_notes TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT DEFAULT 'units',
            low_stock_alert INTEGER DEFAULT 10,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Seed default data
    count = conn.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0]
    if count == 0:
        seed_data = [
            ("Margherita Pizza", "Classic tomato, mozzarella, basil", 12.99, "Pizza"),
            ("Pepperoni Pizza", "Tomato sauce, mozzarella, pepperoni", 14.99, "Pizza"),
            (
                "Caesar Salad",
                "Romaine, parmesan, croutons, caesar dressing",
                8.99,
                "Salads",
            ),
            (
                "Grilled Chicken Wrap",
                "Grilled chicken, lettuce, tomato, wrap",
                10.99,
                "Mains",
            ),
            ("Spaghetti Carbonara", "Pasta, pancetta, egg, parmesan", 13.99, "Pasta"),
            ("Tiramisu", "Coffee-flavored Italian dessert", 6.99, "Desserts"),
            (
                "Chocolate Brownie",
                "Warm chocolate brownie with ice cream",
                7.99,
                "Desserts",
            ),
            ("Iced Tea", "Freshly brewed iced tea", 3.99, "Beverages"),
            ("Fresh Orange Juice", "Freshly squeezed orange juice", 4.99, "Beverages"),
            ("Garlic Bread", "Toasted garlic bread with butter", 4.99, "Sides"),
        ]
        conn.executemany(
            "INSERT INTO menu_items (name, description, price, category) VALUES (?, ?, ?, ?)",
            seed_data,
        )
    if conn.execute("SELECT COUNT(*) FROM tables").fetchone()[0] == 0:
        for i, cap in [(1, 2), (2, 2), (3, 4), (4, 4), (5, 6), (6, 6), (7, 8), (8, 8)]:
            conn.execute(
                "INSERT INTO tables (table_number, capacity, status) VALUES (?, ?, 'available')",
                (i, cap),
            )
    if conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 0:
        inv = [
            ("Flour", 50, "kg"),
            ("Tomato Sauce", 20, "liters"),
            ("Mozzarella Cheese", 15, "kg"),
            ("Pepperoni", 8, "kg"),
            ("Chicken Breast", 10, "kg"),
            ("Pasta", 30, "kg"),
            ("Lettuce", 20, "heads"),
            ("Tomatoes", 30, "kg"),
            ("Olive Oil", 10, "liters"),
            ("Sugar", 25, "kg"),
            ("Cocoa Powder", 5, "kg"),
            ("Ice Cream", 20, "liters"),
        ]
        conn.executemany(
            "INSERT INTO inventory (item_name, quantity, unit) VALUES (?, ?, ?)", inv
        )
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


# ── MENU ──
@app.route("/api/menu", methods=["GET"])
def get_menu():
    category = request.args.get("category")
    conn = get_db()
    if category:
        items = conn.execute(
            "SELECT * FROM menu_items WHERE category = ? AND available = 1 ORDER BY category, name",
            (category,),
        ).fetchall()
    else:
        items = conn.execute(
            "SELECT * FROM menu_items WHERE available = 1 ORDER BY category, name"
        ).fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])


@app.route("/api/menu/categories", methods=["GET"])
def menu_categories():
    conn = get_db()
    cats = conn.execute(
        "SELECT DISTINCT category FROM menu_items WHERE available = 1 ORDER BY category"
    ).fetchall()
    conn.close()
    return jsonify([c["category"] for c in cats])


# ── ORDERS ──
@app.route("/api/orders", methods=["POST"])
def place_order():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    customer_name = data.get("customer_name", "").strip()
    if not customer_name:
        return jsonify({"error": "Customer name required"}), 400
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "At least one item required"}), 400
    conn = get_db()
    table_id = data.get("table_id")
    cur = conn.execute(
        "INSERT INTO orders (customer_name, table_id) VALUES (?, ?)",
        (customer_name, table_id),
    )
    order_id = cur.lastrowid
    if table_id:
        conn.execute("UPDATE tables SET status = 'occupied' WHERE id = ?", (table_id,))
    total = 0.0
    for item in items:
        menu_id = item.get("id")
        qty = item.get("quantity", 1)
        menu = conn.execute(
            "SELECT * FROM menu_items WHERE id = ? AND available = 1", (menu_id,)
        ).fetchone()
        if not menu:
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
            conn.close()
            return jsonify({"error": f"Item {menu_id} not available"}), 400
        conn.execute(
            "INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, special_notes) VALUES (?, ?, ?, ?, ?)",
            (order_id, menu_id, qty, menu["price"], item.get("notes", "")),
        )
        total += menu["price"] * qty
        # Auto-deduct inventory
        for ing in ["Flour", "Tomato Sauce", "Mozzarella Cheese"]:
            conn.execute(
                "UPDATE inventory SET quantity = MAX(0, quantity - 1), updated_at = ? WHERE item_name = ?",
                (datetime.now().isoformat(), ing),
            )
    conn.execute(
        "UPDATE orders SET total = ? WHERE id = ?", (round(total, 2), order_id)
    )
    conn.commit()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id)).fetchone() if False else conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    order_items = conn.execute(
        """
        SELECT oi.*, mi.name as item_name FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id WHERE oi.order_id = ?
    """,
        (order_id,),
    ).fetchall()
    conn.close()
    result = dict(order)
    result["items"] = [dict(oi) for oi in order_items]
    return jsonify(result), 201


@app.route("/api/orders", methods=["GET"])
def list_orders():
    status = request.args.get("status")
    conn = get_db()
    if status:
        orders = conn.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        orders = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ).fetchall()
    orders_list = []
    for o in orders:
        od = dict(o)
        items = conn.execute(
            """
            SELECT oi.*, mi.name as item_name, mi.description as item_desc
            FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        """,
            (o["id"],),
        ).fetchall()
        od["items"] = [dict(i) for i in items]
        orders_list.append(od)
    conn.close()
    return jsonify(orders_list)


@app.route("/api/orders/<int:order_id>", methods=["GET"])
def order_detail(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
    items = conn.execute(
        """
        SELECT oi.*, mi.name as item_name, mi.description as item_desc
        FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id
        WHERE oi.order_id = ?
    """,
        (order_id,),
    ).fetchall()
    conn.close()
    result = dict(order)
    result["items"] = [dict(i) for i in items]
    return jsonify(result)


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def update_order_status(order_id):
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_status = data.get("status", "")
    valid = ["pending", "preparing", "ready", "served", "completed", "cancelled"]
    if new_status not in valid:
        return jsonify({"error": f"Status must be one of: {', '.join(valid)}"}), 400
    conn = get_db()
    order = conn.execute("SELECT id, table_id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    if new_status in ("completed", "cancelled") and order["table_id"]:
        active = conn.execute(
            "SELECT id FROM orders WHERE table_id = ? AND id != ? AND status IN ('pending', 'preparing', 'ready', 'served')",
            (order["table_id"], order_id),
        ).fetchone()
        if not active:
            conn.execute("UPDATE tables SET status = 'available' WHERE id = ?", (order["table_id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Order status updated to '{new_status}'"})


@app.route("/api/orders/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id):
    conn = get_db()
    order = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Order cancelled"})


# ── TABLES ──
@app.route("/api/tables", methods=["GET"])
def list_tables():
    status = request.args.get("status")
    conn = get_db()
    if status:
        tables = conn.execute(
            "SELECT * FROM tables WHERE status = ? ORDER BY table_number", (status,)
        ).fetchall()
    else:
        tables = conn.execute("SELECT * FROM tables ORDER BY table_number").fetchall()
    conn.close()
    return jsonify([dict(t) for t in tables])


@app.route("/api/tables/<int:table_id>", methods=["PATCH"])
def update_table(table_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "")
    valid = ["available", "occupied", "reserved", "maintenance"]
    if new_status not in valid:
        return jsonify({"error": f"Status must be: {', '.join(valid)}"}), 400
    conn = get_db()
    t = conn.execute("SELECT id FROM tables WHERE id = ?", (table_id,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "Table not found"}), 404
    conn.execute("UPDATE tables SET status = ? WHERE id = ?", (new_status, table_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM tables WHERE id = ?", (table_id,)).fetchone()
    conn.close()
    return jsonify(dict(updated))


@app.route("/api/tables/available", methods=["GET"])
def available_tables():
    capacity = request.args.get("capacity", type=int)
    conn = get_db()
    if capacity:
        tables = conn.execute(
            "SELECT * FROM tables WHERE status = 'available' AND capacity >= ? ORDER BY capacity",
            (capacity,),
        ).fetchall()
    else:
        tables = conn.execute(
            "SELECT * FROM tables WHERE status = 'available' ORDER BY table_number"
        ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tables])


@app.route("/api/reservations", methods=["POST"])
def make_reservation():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = data.get("customer_name", "").strip()
    if not name:
        return jsonify({"error": "Customer name required"}), 400
    party_size = int(data.get("party_size") or 1)
    date = data.get("reservation_date", "")
    time = data.get("reservation_time", "")
    if not date or not time:
        return jsonify({"error": "Date and time required"}), 400
    conn = get_db()
    table_id = data.get("table_id")
    if not table_id:
        table_row = conn.execute(
            """
            SELECT id FROM tables
            WHERE capacity >= ? AND id NOT IN (
                SELECT table_id FROM reservations
                WHERE reservation_date = ? AND reservation_time = ? AND status IN ('confirmed', 'seated')
            )
            ORDER BY capacity LIMIT 1
        """,
            (party_size, date, time),
        ).fetchone()
        if not table_row:
            conn.close()
            return jsonify(
                {"error": "No table available for party size of " + str(party_size)}
            ), 400
        table_id = table_row[0]
    else:
        table_id = int(table_id)
        exists = conn.execute("SELECT id FROM tables WHERE id = ?", (table_id,)).fetchone()
        if not exists:
            conn.close()
            return jsonify({"error": "Specified table not found"}), 404

    conflict = conn.execute(
        """
        SELECT id FROM reservations WHERE table_id = ? AND reservation_date = ? AND reservation_time = ?
        AND status IN ('confirmed', 'seated') LIMIT 1
    """,
        (table_id, date, time),
    ).fetchone()
    if conflict:
        conn.close()
        return jsonify({"error": f"Table is already booked for {time} on {date}"}), 400
    cur = conn.execute(
        """
        INSERT INTO reservations (table_id, customer_name, customer_phone, customer_email, party_size, reservation_date, reservation_time, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            table_id,
            name,
            data.get("customer_phone", ""),
            data.get("customer_email", ""),
            party_size,
            date,
            time,
            data.get("notes", ""),
        ),
    )
    conn.execute("UPDATE tables SET status = 'reserved' WHERE id = ?", (table_id,))
    conn.commit()
    res = conn.execute(
        "SELECT r.*, t.table_number, t.capacity FROM reservations r JOIN tables t ON r.table_id = t.id WHERE r.id = ?",
        (cur.lastrowid,),
    ).fetchone()
    conn.close()
    return jsonify(dict(res)), 201


@app.route("/api/reservations", methods=["GET"])
def list_reservations():
    status = request.args.get("status")
    date = request.args.get("date")
    conn = get_db()
    if status and date:
        res = conn.execute(
            "SELECT r.*, t.table_number, t.capacity FROM reservations r JOIN tables t ON r.table_id = t.id WHERE r.status = ? AND r.reservation_date = ? ORDER BY r.reservation_time",
            (status, date),
        ).fetchall()
    elif date:
        res = conn.execute(
            "SELECT r.*, t.table_number, t.capacity FROM reservations r JOIN tables t ON r.table_id = t.id WHERE r.reservation_date = ? ORDER BY r.reservation_time",
            (date,),
        ).fetchall()
    else:
        res = conn.execute(
            "SELECT r.*, t.table_number, t.capacity FROM reservations r JOIN tables t ON r.table_id = t.id ORDER BY r.reservation_date, r.reservation_time"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in res])


@app.route("/api/reservations/<int:res_id>", methods=["PATCH"])
def update_reservation(res_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "")
    valid = ["confirmed", "seated", "completed", "cancelled", "no-show"]
    if new_status not in valid:
        return jsonify({"error": f"Status must be: {', '.join(valid)}"}), 400
    conn = get_db()
    r = conn.execute(
        "SELECT id, table_id, status FROM reservations WHERE id = ?", (res_id,)
    ).fetchone()
    if not r:
        conn.close()
        return jsonify({"error": "Reservation not found"}), 404
    conn.execute(
        "UPDATE reservations SET status = ? WHERE id = ?", (new_status, res_id)
    )
    if new_status == "cancelled" and r["status"] != "completed":
        conn.execute(
            "UPDATE tables SET status = 'available' WHERE id = ?", (r["table_id"],)
        )
    conn.commit()
    conn.close()
    return jsonify({"message": f"Reservation status: {new_status}"})


@app.route("/api/reservations/<int:res_id>", methods=["DELETE"])
def cancel_reservation(res_id):
    conn = get_db()
    r = conn.execute(
        "SELECT table_id, status FROM reservations WHERE id = ?", (res_id,)
    ).fetchone()
    if not r:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    conn.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
    if r["status"] in ("confirmed", "seated"):
        conn.execute(
            "UPDATE tables SET status = 'available' WHERE id = ?", (r["table_id"],)
        )
    conn.commit()
    conn.close()
    return jsonify({"message": "Reservation cancelled"})


# ── INVENTORY ──
@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    low = request.args.get("low", "false") == "true"
    conn = get_db()
    if low:
        items = conn.execute(
            "SELECT * FROM inventory WHERE quantity <= low_stock_alert ORDER BY quantity ASC"
        ).fetchall()
    else:
        items = conn.execute("SELECT * FROM inventory ORDER BY item_name").fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])


@app.route("/api/inventory/<int:item_id>", methods=["PATCH"])
def update_inventory(item_id):
    data = request.get_json(silent=True) or {}
    delta = data.get("delta", 0)
    new_qty = data.get("quantity")
    conn = get_db()
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if not item:
        conn.close()
        return jsonify({"error": "Item not found"}), 404
    if new_qty is not None:
        conn.execute(
            "UPDATE inventory SET quantity = ?, updated_at = ? WHERE id = ?",
            (new_qty, datetime.now().isoformat(), item_id),
        )
    elif delta:
        conn.execute(
            "UPDATE inventory SET quantity = MAX(0, quantity + ?), updated_at = ? WHERE id = ?",
            (delta, datetime.now().isoformat(), item_id),
        )
    updated = conn.execute(
        "SELECT * FROM inventory WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return jsonify(dict(updated))


@app.route("/api/inventory/low-stock", methods=["GET"])
def low_stock_alerts():
    conn = get_db()
    items = conn.execute(
        "SELECT * FROM inventory WHERE quantity <= low_stock_alert ORDER BY quantity ASC"
    ).fetchall()
    conn.close()
    return jsonify({"alerts": [dict(i) for i in items], "count": len(items)})


# ── REPORTS ──
@app.route("/api/reports/daily-sales", methods=["GET"])
def daily_sales():
    date = request.args.get("date")
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    orders = conn.execute(
        """
        SELECT o.id, o.customer_name, o.total, o.status, o.created_at, COUNT(oi.id) as item_count
        FROM orders o LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE date(o.created_at) = ? GROUP BY o.id ORDER BY o.created_at
    """,
        (date,),
    ).fetchall()
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM orders WHERE status != 'cancelled' AND date(created_at) = ?",
        (date,),
    ).fetchone()[0]
    order_count = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE date(created_at) = ?", (date,)
    ).fetchone()[0]
    conn.close()
    return jsonify(
        {
            "date": date,
            "orders": [dict(o) for o in orders],
            "total_revenue": round(total_revenue, 2),
            "order_count": order_count,
        }
    )


@app.route("/api/reports/summary", methods=["GET"])
def report_summary():
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    total_rev = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM orders WHERE status != 'cancelled' AND date(created_at) = ?",
        (today,),
    ).fetchone()[0]
    order_cnt = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE date(created_at) = ?", (today,)
    ).fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
    ).fetchone()[0]
    low_stock = conn.execute(
        "SELECT COUNT(*) FROM inventory WHERE quantity <= low_stock_alert"
    ).fetchone()[0]
    reservations = conn.execute(
        "SELECT COUNT(*) FROM reservations WHERE date(reservation_date) >= ? AND status = 'confirmed'",
        (today,),
    ).fetchone()[0]
    conn.close()
    return jsonify(
        {
            "date": today,
            "total_revenue": round(total_rev, 2),
            "orders_today": order_cnt,
            "pending_orders": pending,
            "low_stock_items": low_stock,
            "upcoming_reservations": reservations,
        }
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5003)
