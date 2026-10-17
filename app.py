
from flask import Flask, request, jsonify
from datetime import datetime
import json
import re

app = Flask(__name__)

with open("clean_orders.json", "r", encoding="utf-8") as file:
    orders = json.load(file)


def matches_filters(order, question):
    q = question.lower()

    # Match region if explicitly mentioned
    regions = {o["region"].lower() for o in orders}
    for region in regions:
        if re.search(r"\b" + re.escape(region) + r"\b", q):
            if order["region"].lower() != region:
                return False

    # Match product if explicitly mentioned
    products = {o["product"].lower() for o in orders}
    for product in products:
        if product in q and order["product"].lower() != product:
            return False

    # Match customer ID if explicitly mentioned
    customer_ids = {o["customer"].lower() for o in orders}
    for customer in customer_ids:
        if customer in q and order["customer"].lower() != customer:
            return False

    # Match year and month when present
    months = {
        "january": 1, "february": 2, "march": 3,
        "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12
    }

    for month_name, month_number in months.items():
        if month_name in q:
            date_value = datetime.fromisoformat(
                order["created_at"].replace("Z", "+00:00")
            )
            if date_value.month != month_number:
                return False

    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        year = int(year_match.group(1))
        date_value = datetime.fromisoformat(
            order["created_at"].replace("Z", "+00:00")
        )
        if date_value.year != year:
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

    if "refund" in q:
        wanted_status = "refunded"
    elif "revenue" in q or "sales" in q or "paid" in q:
        wanted_status = "paid"
    else:
        return jsonify({
            "error": "Please ask about revenue, sales, or refunds."
        }), 400

    selected = [
        order for order in orders
        if order["status"] == wanted_status
        and matches_filters(order, question)
    ]

    total_cents = sum(
        order["amount_usd_cents"] for order in selected
    )

    return jsonify({"answer": total_cents})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
