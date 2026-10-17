```python
from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re

app = Flask(__name__)

with open("clean_orders.json", "r", encoding="utf-8") as file:
    orders = json.load(file)


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12
}


def order_matches(order, question):
    q = question.lower()

    # Filter by region
    for region in {o["region"].lower() for o in orders}:
        if re.search(r"\b" + re.escape(region) + r"\b", q):
            if order["region"].lower() != region:
                return False

    # Filter by product
    for product in {o["product"].lower() for o in orders}:
        if re.search(r"\b" + re.escape(product) + r"\b", q):
            if order["product"].lower() != product:
                return False

    # Filter by customer ID
    for customer in {o["customer"].lower() for o in orders}:
        if re.search(r"\b" + re.escape(customer) + r"\b", q):
            if order["customer"].lower() != customer:
                return False

    # Convert dates to the required timezone
    order_date = datetime.fromisoformat(
        order["created_at"].replace("Z", "+00:00")
    )

    if order_date.tzinfo is not None:
        order_date = order_date.astimezone(
            ZoneInfo("Asia/Kolkata")
        )

    # Filter by month
    for month_name, month_number in MONTHS.items():
        if re.search(r"\b" + month_name + r"\b", q):
            if order_date.month != month_number:
                return False

    # Filter by year
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match and order_date.year != int(year_match.group(1)):
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

    # Determine the requested order status
    if re.search(r"\b(refund|refunded|refunds)\b", q):
        wanted_status = "refunded"

    elif re.search(
        r"\b(revenue|sales|paid|earn|earned|income|turnover|sold)\b",
        q
    ):
        wanted_status = "paid"

    else:
        return jsonify({"error": "Unsupported question"}), 400

    # Select matching orders
    selected = [
        order for order in orders
        if order["status"].lower() == wanted_status
        and order_matches(order, question)
    ]

    # Average must be checked BEFORE count because
    # "how many US dollars" asks for an amount, not order count.
    if re.search(r"\b(average|avg|mean)\b", q) or (
        "how many" in q and re.search(
            r"\b(dollars|usd|money)\b", q
        )
    ):
        answer = round(
            sum(order["amount_usd_cents"] for order in selected)
            / len(selected)
        ) if selected else 0

    elif re.search(r"\b(count|how many|number of)\b", q):
        answer = len(selected)

    else:
        answer = sum(
            order["amount_usd_cents"] for order in selected
        )

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```
