# Inventory Management System

A Flask REST API for managing retail inventory, with a command-line interface
and OpenFoodFacts integration to pull in real product data by barcode or name.

## Features

- **CRUD REST API** (Flask): create, read, update (PATCH), and delete items
- **Helper routes**: health check, low-stock report, name/brand search
- **External API integration**: look up products on [OpenFoodFacts](https://world.openfoodfacts.org/data)
  and import them directly into the inventory
- **CLI**: manage everything from the terminal
- **Mock OpenFoodFacts database**: an array shaped like the real API response, used to seed the inventory and to run fully offline
- **Interactive menu** (`menu` command) plus scriptable CLI commands
- **Tests**: 85 unit tests; external HTTP calls are mocked so the suite runs offline



## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the API

```bash
python -m inventory.app
# Serving on http://127.0.0.1:5000 with debug mode on, seeded with 8 mock products
```

No internet? Run fully offline using the mock OpenFoodFacts array:

```bash
OFF_USE_MOCK=1 python -m inventory.app          # Windows PowerShell: $env:OFF_USE_MOCK="1"
OFF_USE_MOCK=1 python -m inventory.cli lookup --name almond
```

## Use the CLI


**Item fields:** `id`, `name`, `brand`, `barcode`, `category`, `price`, `stock`,
`ingredients`, `quantity_label`, `image_url`.

**Status codes:** `200` OK, `201` created, `400` validation error,
`404` not found, `502` OpenFoodFacts unreachable.

### Example with curl

```bash
curl -X POST http://127.0.0.1:5000/inventory \
  -H "Content-Type: application/json" \
  -d '{"name": "Oat Milk", "price": 3.5, "stock": 20}'

curl -X PATCH http://127.0.0.1:5000/inventory/1 \
  -H "Content-Type: application/json" -d '{"stock": 15}'

curl -X POST http://127.0.0.1:5000/inventory/import \
  -H "Content-Type: application/json" \
  -d '{"barcode": "3017620422003", "price": 4.99, "stock": 12}'
```

## Debugging with Postman

Import `docs/inventory.postman_collection.json` into Postman (it uses a
`base_url` variable set to `http://127.0.0.1:5000`). The collection has a
request for every route, including two that deliberately trigger 400/404.
The server runs in Flask debug mode, so code changes reload automatically and
errors show a traceback.

## Run the tests

```bash
python -m unittest discover -s tests -t . -v
# or, with pytest:
pytest -v
```

## Design notes

- **In-memory storage.** Items live in a Python list on the app object, as the
  lab specifies. Data resets when the server restarts. Swapping in SQLite or
  SQLAlchemy would only require changing the helpers inside `create_app()`.
- **App factory.** `create_app()` builds a fresh app (and empty inventory) per
  call, so every test is isolated.
- **Normalized external data.** `openfoodfacts.py` converts OpenFoodFacts'
  payload into our own field names, so the rest of the code never depends on
  the external format.
- **Clear errors.** Network failures from OpenFoodFacts surface as `502`
  rather than crashing; invalid input returns `400` with a message.
- **Mocked tests.** Tests never hit the real network, so they are fast and
  deterministic.

## Possible improvements

- Persistent database (SQLite/PostgreSQL)
- Authentication for the admin portal
- Pagination and sorting on `GET /inventory`
- Duplicate-barcode detection on import
