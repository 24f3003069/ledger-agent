
from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re

app = Flask(__name__)

# Load the prepared order data.
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
    "december": 12,
}

TIMEZONE = ZoneInfo("Asia/Kolkata")


def contains_word(text, word):
    return bool(
        re.search(r"\b" + re.escape(word) + r"\b", text)
    )


# Prepare searchable values once when the application starts.
REGIONS = sorted(
    {str(o["region"]).lower() for o in orders},
    key=len,
    reverse=True,
)

PRODUCTS = sorted(
    {str(o["product"]).lower() for o in orders},
    key=len,
    reverse=True,
)

CUSTOMERS = sorted(
    {str(o["customer"]).lower() for o in orders},
    key=len,
    reverse=True,
)


def get_order_date(order):
    date_value = datetime.fromisoformat(
        order["created_at"].replace("Z", "+00:00")
    )

    if date_value.tzinfo is not None:
        date_value = date_value.astimezone(TIMEZONE)

    return date_value


def get_matching_orders(question):
    q = question.lower()

    # Identify the requested order status.
    if re.search(r"\b(refund|refunded|refunds)\b", q):
        wanted_status = "refunded"
    elif re.search(
        r"\b(revenue|sales|paid|earn|earned|income|turnover|sold)\b",
        q,
    ):
        wanted_status = "paid"
    else:
        return None

    # Find region filters mentioned in the question.
    regions = {
        region
        for region in REGIONS
        if contains_word(q, region)
    }

    # Find product filters mentioned in the question.
    products = {
        product
        for product in PRODUCTS
        if contains_word(q, product)
    }

    # Find customer filters mentioned in the question.
    customers = {
        customer
        for customer in CUSTOMERS
        if contains_word(q, customer)
    }

    # Find month and year filters.
    month_number = None

    for month_name, number in MONTHS.items():
        if contains_word(q, month_name):
            month_number = number
            break

    year_match = re.search(r"\b(20\d{2})\b", q)
    year = int(year_match.group(1)) if year_match else None

    selected = []

    for order in orders:
        if str(order["status"]).lower() != wanted_status:
            continue

        if regions and str(order["region"]).lower() not in regions:
            continue

        if products and str(order["product"]).lower() not in products:
            continue

        if customers and str(order["customer"]).lower() not in customers:
            continue

        # Only parse dates when a date filter was requested.
        if month_number is not None or year is not None:
            order_date = get_order_date(order)

            if (
                month_number is not None
                and order_date.month != month_number
            ):
                continue

            if year is not None and order_date.year != year:
                continue

        selected.append(order)

    return selected


def get_amount_cents(order):
    return int(order.get("amount_usd_cents", 0))


def is_top_product_question(q):
    return bool(
        re.search(
            r"\b(top|best|highest|most)\s*[- ]?\s*"
            r"(selling|sold|selling\s+product|revenue|"
            r"profitable)\b",
            q,
        )
        or re.search(
            r"\b(which|what)\s+product\b.*"
            r"\b(most|highest|top|best|greatest)\b",
            q,
        )
        or re.search(
            r"\b(product|products)\b.*"
            r"\b(highest|most|maximum|largest)\s+revenue\b",
            q,
        )
    )


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

    selected = get_matching_orders(question)

    if selected is None:
        return jsonify({"error": "Unsupported question"}), 400

    # TOP-SELLING PRODUCT: group paid revenue by product.
    # This must be checked before the ordinary revenue sum.
    if is_top_product_question(q):
        product_revenue = {}

        for order in selected:
            product = str(order["product"])
            product_revenue[product] = (
                product_revenue.get(product, 0)
                + get_amount_cents(order)
            )

        if not product_revenue:
            answer = None
        else:
            answer = max(
                product_revenue,
                key=product_revenue.get,
            )

        return jsonify({"answer": answer})

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
        # Return average in USD dollars, rounded to 2 decimals.
        answer = (
            round(
                sum(get_amount_cents(o) for o in selected)
                / len(selected)
                / 100,
                2,
            )
            if selected
            else 0
        )

    elif is_count:
        answer = len(selected)

    else:
        # Return total revenue in USD dollars.
        answer = round(
            sum(
                get_amount_cents(order)
                for order in selected
            ) / 100,
            2
        )

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
