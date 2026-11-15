# Route Plan

Planning document: for each route, what goes in, what comes out, what changes
in the data array, and when the CLI triggers it.

**Data store:** a Python list of dicts on the Flask app (`app.config["INVENTORY"]`).
**Item shape:**
`id, name, brand, barcode, category, price, stock, ingredients, quantity_label, image_url`

**Mock OpenFoodFacts DB:** `inventory/mock_data.py` holds an array shaped like
the real API (`{"status": 1, "product": {"product_name", "brands", "ingredients_text", ...}}`).
It seeds the inventory on startup and answers lookups when `OFF_USE_MOCK=1`.

## Core CRUD routes

| Route | Input | Output | Changes in the array | CLI trigger |
|---|---|---|---|---|
| `GET /inventory` | optional `?q=` (matches name/brand) | `200` list of items | nothing | `list [--search]`, menu 1 |
| `GET /inventory/<id>` | `id` in URL | `200` item / `404` | nothing | `get <id>`, menu 2 |
| `POST /inventory` | JSON: `name` (required), optional `brand, barcode, category, price, stock, ...` | `201` new item (with generated `id`) / `400` | **appends** an item | `add <name> --price --stock`, menu 3 |
| `PATCH /inventory/<id>` | `id` + JSON with any subset of fields | `200` updated item / `400` / `404` | **modifies** only the given fields of one item | `update <id> --price --stock`, menu 4 |
| `DELETE /inventory/<id>` | `id` in URL | `200` message / `404` | **removes** the item | `delete <id>`, menu 5 |

## Helper routes

| Route | Input | Output | Changes | CLI trigger |
|---|---|---|---|---|
| `GET /health` | none | `200 {"status":"ok"}` | nothing | (Postman / monitoring) |
| `GET /inventory/low-stock` | optional `?threshold=` (default 5) | `200` items with `stock <= threshold` | nothing | `low-stock [--threshold]`, menu 9 |

## External API routes (OpenFoodFacts)

| Route | Input | Output | Changes | CLI trigger |
|---|---|---|---|---|
| `GET /external/barcode/<barcode>` | barcode in URL | `200` normalized product / `404` / `502` | nothing | `lookup --barcode`, menu 6 |
| `GET /external/search?name=` | product name | `200` list (up to 5) / `400` / `502` | nothing | `lookup --name`, menu 6 |
| `POST /inventory/import` | JSON: `barcode` **or** `name`; optional `price`, `stock` | `201` new item / `400` / `404` / `502` | **appends** an item built from API data + our price/stock | `import --barcode/--name`, menu 7 |
| `POST /inventory/<id>/enrich` | `id` in URL (item needs a `barcode`) | `200` updated item / `400` / `404` / `502` | **fills empty fields** (brand, category, ingredients, ...) of an existing item; never overwrites | `enrich <id>`, menu 8 |

## Error handling

| Code | Meaning |
|---|---|
| 400 | Invalid input (missing name, negative price/stock, unknown field, no barcode on enrich) |
| 404 | Item or product not found |
| 502 | OpenFoodFacts unreachable / bad response |

The CLI turns these into readable messages (`Error 404: Item not found.`) and
reports "Could not connect" if the Flask server isn't running.

## Typical user flows

1. **Receive new stock of a known product:** `lookup --barcode` (check it's right), then `import --barcode --price --stock`.
2. **Sale / restock:** `update <id> --stock <n>`.
3. **Complete a hand-entered item:** `add` with a barcode, then `enrich <id>`.
4. **Morning check:** `low-stock --threshold 10`.
