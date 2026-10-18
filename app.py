from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re

app = Flask(__name__)

with open("clean_orders.json", "r", encoding="utf-8") as file:
    orders = json.load(file)

MONTHS = {
    "january": 1, "february": 2, "march": 3,
    "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12
}

# Prepare lookup values once instead of rebuilding them for every order.
REGIONS = sorted(
    {o["region"].lower() for o in orders},
    key=len, reverse=True
)
PRODUCTS = sorted(
    {o["product"].lower() for o in orders},
    key=len, reverse=True
)
CUSTOMERS = sorted(
    {o["customer"].lower() for o in orders},
    key=len, reverse=True
)


def order_matches(order, regions, products, customers,
                  month_number, year):
    if regions and order["region"].lower() not in regions:
        return False

    if products and order["product"].lower() not in products:
        return False

    if customers and order["customer"].lower() not in customers:
        return False

    if month_number is not None or year is not None:
        date_value = datetime.fromisoformat(
            order["created_at"].replace("Z", "+00:00")
        )

        if date_value.tzinfo is not None:
            date_value = date_value.astimezone(
                ZoneInfo("Asia/Kolkata")
            )

        if month_number is not None and date_value.month != month_number:
            return False

        if year is not None and date_value.year != year:
            return False

    return True


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Acme Appliances Ledger Agent is running"
    })


@app.route("/", methods=["POST"])
def answer_question():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Please provide a question"}), 400

    q = question.lower()

    # Determine the requested status.
    if re.search(r"\b(refund|refunded|refunds)\b", q):
        wanted_status = "refunded"
    elif re.search(
        r"\b(revenue|sales|paid|earn|earned|income|turnover|sold)\b",
        q
    ):
        wanted_status = "paid"
    else:
        return jsonify({"error": "Unsupported question"}), 400

    # Identify filters once per question.
    regions = {
        region for region in REGIONS
        if re.search(r"\b" + re.escape(region) + r"\b", q)
    }

    products = {
        product for product in PRODUCTS
        if re.search(r"\b" + re.escape(product) + r"\b", q)
    }

    customers = {
        customer for customer in CUSTOMERS
        if re.search(r"\b" + re.escape(customer) + r"\b", q)
    }

    month_number = None
    for month_name, number in MONTHS.items():
        if re.search(r"\b" + month_name + r"\b", q):
            month_number = number
            break

    year_match = re.search(r"\b(20\d{2})\b", q)
    year = int(year_match.group(1)) if year_match else None

    # Filter orders efficiently.
    selected = [
        order for order in orders
        if order["status"].lower() == wanted_status
        and order_matches(
            order, regions, products, customers,
            month_number, year
        )
    ]

    # Average questions must be checked before count questions.
    is_average = bool(
        re.search(r"\b(average|avg|mean)\b", q)
    ) or (
        "how many" in q
        and re.search(r"\b(dollars|usd|money)\b", q)
    )

    is_count = bool(
        re.search(r"\b(count|how many|number of)\b", q)
    )

    if is_average:
        answer = round(
            sum(o["amount_usd_cents"] for o in selected)
            / len(selected) / 100,
            2
        ) if selected else 0

    elif is_count:
        answer = len(selected)

    else:
        answer = sum(
            o["amount_usd_cents"] for o in selected
        )

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
