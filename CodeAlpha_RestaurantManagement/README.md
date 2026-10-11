# Restaurant Management System (CodeAlpha_RestaurantManagement)

Complete restaurant point-of-sale, table assignment, reservations, inventory, and reporting system.

## Features

- Menu categorized by item types with seed data.
- Live order creation with table assignment and item detail breakdowns.
- Automated inventory deduction on order placement.
- Table management with `available`, `occupied`, `reserved`, and `maintenance` states.
- Conflict-free reservation booking by table, date, and time slot.
- Low-stock inventory alerts and stock level adjustments.
- Real-time daily sales revenue dashboard and metrics.

## How to Run

```bash
# From this directory:
source .venv/bin/activate
python app.py
```

Access the application at [http://localhost:5003](http://localhost:5003).

## Testing

```bash
pytest test_restaurant_management.py -v
```
