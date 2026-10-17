
import json
from datetime import datetime

# Load all downloaded orders
with open("all_orders.json", "r", encoding="utf-8") as file:
    orders = json.load(file)

# Load currency exchange rates
with open("rates.json", "r", encoding="utf-8") as file:
    rates_data = json.load(file)

rates = rates_data["usd_per_unit"]

# Keep only the latest version of each order ID
latest_orders = {}

for order in orders:
    order_id = order["id"]

    updated_at = datetime.fromisoformat(
        order["updated_at"].replace("Z", "+00:00")
    )

    if (
        order_id not in latest_orders
        or updated_at > datetime.fromisoformat(
            latest_orders[order_id]["updated_at"].replace("Z", "+00:00")
        )
    ):
        latest_orders[order_id] = order

# Convert each order amount to USD cents
clean_orders = []

for order in latest_orders.values():
    cleaned = order.copy()

    currency = order["currency"]
    amount_usd = order["amount"] * rates[currency]

    cleaned["amount_usd_cents"] = round(amount_usd * 100)
    clean_orders.append(cleaned)

# Save the cleaned records
with open("clean_orders.json", "w", encoding="utf-8") as file:
    json.dump(clean_orders, file, indent=2)

print("Original records:", len(orders))
print("Unique orders:", len(clean_orders))
print("Cleaned data saved to clean_orders.json")
print("First cleaned order:", clean_orders[0])
print("Currencies found:", sorted(set(o["currency"] for o in clean_orders)))