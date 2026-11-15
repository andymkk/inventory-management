"""Flask REST API for the inventory management system."""
from flask import Flask, jsonify, request

from inventory import openfoodfacts as off
from inventory.mock_data import MOCK_OFF_DATABASE, SEED_PRICING

EDITABLE_FIELDS = {
    "name", "brand", "barcode", "category", "price", "stock",
    "ingredients", "quantity_label", "image_url",
}
LOW_STOCK_THRESHOLD = 5


def create_app(seed=False):
    """Build the app. With seed=True the inventory starts with mock data."""
    app = Flask(__name__)
    # In-memory "database" (an array of dicts). Stored on the app so each
    # test gets a fresh, isolated copy.
    app.config["INVENTORY"] = []
    app.config["NEXT_ID"] = 1

    # ---------- helpers ----------
    def find_item(item_id):
        return next((i for i in app.config["INVENTORY"] if i["id"] == item_id), None)

    def error(message, status):
        return jsonify({"error": message}), status

    def validate(data, partial=False):
        """Return an error message string, or None if the data is valid."""
        if not isinstance(data, dict):
            return "Request body must be a JSON object."
        unknown = set(data) - EDITABLE_FIELDS
        if unknown:
            return f"Unknown field(s): {', '.join(sorted(unknown))}."
        if not partial and not data.get("name"):
            return "'name' is required."
        if "price" in data and (
            isinstance(data["price"], bool)
            or not isinstance(data["price"], (int, float))
            or data["price"] < 0
        ):
            return "'price' must be a non-negative number."
        if "stock" in data and (
            isinstance(data["stock"], bool)
            or not isinstance(data["stock"], int)
            or data["stock"] < 0
        ):
            return "'stock' must be a non-negative integer."
        return None

    def add_item(data):
        item = {
            "id": app.config["NEXT_ID"],
            "name": data["name"],
            "brand": data.get("brand", ""),
            "barcode": data.get("barcode", ""),
            "category": data.get("category", ""),
            "price": data.get("price", 0.0),
            "stock": data.get("stock", 0),
            "ingredients": data.get("ingredients", ""),
            "quantity_label": data.get("quantity_label", ""),
            "image_url": data.get("image_url", ""),
        }
        app.config["NEXT_ID"] += 1
        app.config["INVENTORY"].append(item)
        return item

    # ---------- helper routes ----------
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/inventory/low-stock")
    def low_stock():
        threshold = request.args.get("threshold", LOW_STOCK_THRESHOLD, type=int)
        items = [i for i in app.config["INVENTORY"] if i["stock"] <= threshold]
        return jsonify(items)

    # ---------- CRUD ----------
    @app.get("/inventory")
    def list_items():
        items = app.config["INVENTORY"]
        q = request.args.get("q", "").lower()
        if q:
            items = [i for i in items if q in i["name"].lower() or q in i["brand"].lower()]
        return jsonify(items)

    @app.get("/inventory/<int:item_id>")
    def get_item(item_id):
        item = find_item(item_id)
        return jsonify(item) if item else error("Item not found.", 404)

    @app.post("/inventory")
    def create_item():
        data = request.get_json(silent=True)
        problem = validate(data)
        if problem:
            return error(problem, 400)
        return jsonify(add_item(data)), 201

    @app.patch("/inventory/<int:item_id>")
    def update_item(item_id):
        item = find_item(item_id)
        if not item:
            return error("Item not found.", 404)
        data = request.get_json(silent=True)
        problem = validate(data, partial=True)
        if problem:
            return error(problem, 400)
        item.update(data)
        return jsonify(item)

    @app.delete("/inventory/<int:item_id>")
    def delete_item(item_id):
        item = find_item(item_id)
        if not item:
            return error("Item not found.", 404)
        app.config["INVENTORY"].remove(item)
        return jsonify({"message": f"Item {item_id} deleted."})

    # ---------- external API routes ----------
    @app.get("/external/barcode/<barcode>")
    def external_barcode(barcode):
        try:
            product = off.fetch_by_barcode(barcode)
        except off.ExternalAPIError as exc:
            return error(str(exc), 502)
        return jsonify(product) if product else error("Product not found.", 404)

    @app.get("/external/search")
    def external_search():
        name = request.args.get("name", "").strip()
        if not name:
            return error("Query parameter 'name' is required.", 400)
        try:
            return jsonify(off.search_by_name(name))
        except off.ExternalAPIError as exc:
            return error(str(exc), 502)

    @app.post("/inventory/import")
    def import_item():
        """Fetch a product from OpenFoodFacts and add it to the inventory.

        Body: {"barcode": "..."} or {"name": "..."}, plus optional
        "price" and "stock" for our own bookkeeping.
        """
        data = request.get_json(silent=True) or {}
        barcode, name = data.get("barcode"), data.get("name")
        if not barcode and not name:
            return error("Provide 'barcode' or 'name'.", 400)

        problem = validate({k: data[k] for k in ("price", "stock") if k in data}, partial=True)
        if problem:
            return error(problem, 400)

        try:
            if barcode:
                product = off.fetch_by_barcode(barcode)
            else:
                results = off.search_by_name(name, limit=1)
                product = results[0] if results else None
        except off.ExternalAPIError as exc:
            return error(str(exc), 502)

        if not product:
            return error("Product not found on OpenFoodFacts.", 404)

        product["price"] = data.get("price", 0.0)
        product["stock"] = data.get("stock", 0)
        return jsonify(add_item(product)), 201

    @app.post("/inventory/<int:item_id>/enrich")
    def enrich_item(item_id):
        """Fill the item's EMPTY fields using OpenFoodFacts (matched by barcode).

        Existing values (name, price, stock, anything already filled) are kept.
        """
        item = find_item(item_id)
        if not item:
            return error("Item not found.", 404)
        if not item["barcode"]:
            return error("Item has no barcode to look up.", 400)
        try:
            product = off.fetch_by_barcode(item["barcode"])
        except off.ExternalAPIError as exc:
            return error(str(exc), 502)
        if not product:
            return error("Product not found on OpenFoodFacts.", 404)
        for field in ("brand", "category", "ingredients", "quantity_label", "image_url"):
            if not item[field] and product.get(field):
                item[field] = product[field]
        return jsonify(item)

    # ---------- seed data ----------
    if seed:
        for entry in MOCK_OFF_DATABASE:
            product = off.fetch_by_barcode_from_entry(entry)
            price, stock = SEED_PRICING.get(entry["code"], (0.0, 0))
            product.update(price=price, stock=stock)
            add_item(product)

    return app


if __name__ == "__main__":
    # OFF_USE_MOCK=1 python -m inventory.app   -> run fully offline
    create_app(seed=True).run(debug=True)
