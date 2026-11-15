"""Thin client for the OpenFoodFacts API.

Every function returns a *normalized* product dict that matches the fields
used by our inventory (name, brand, barcode, ...), so the rest of the app
never needs to know the shape of the OpenFoodFacts payload.
"""
import os

import requests

from inventory.mock_data import MOCK_OFF_DATABASE

BASE_URL = "https://world.openfoodfacts.org"
HEADERS = {"User-Agent": "InventoryManagementLab/1.0 (student project)"}
TIMEOUT = 10


class ExternalAPIError(Exception):
    """Raised when the external API is unreachable or returns bad data."""


def use_mock():
    """True when OFF_USE_MOCK=1: answer from the mock array, no network."""
    return os.environ.get("OFF_USE_MOCK") == "1"


def _mock_to_raw(entry):
    return {**entry["product"], "code": entry["code"]}


def _normalize(raw):
    """Convert a raw OpenFoodFacts product into our inventory fields."""
    return {
        "name": raw.get("product_name") or "Unknown product",
        "brand": raw.get("brands", ""),
        "barcode": str(raw.get("code") or raw.get("_id") or ""),
        "category": (raw.get("categories") or "").split(",")[0].strip(),
        "ingredients": raw.get("ingredients_text", ""),
        "quantity_label": raw.get("quantity", ""),
        "image_url": raw.get("image_url", ""),
    }


def fetch_by_barcode(barcode):
    """Return a normalized product for a barcode, or None if not found."""
    if use_mock():
        entry = next((e for e in MOCK_OFF_DATABASE if e["code"] == str(barcode)), None)
        return _normalize(_mock_to_raw(entry)) if entry else None
    url = f"{BASE_URL}/api/v2/product/{barcode}.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalAPIError(f"OpenFoodFacts request failed: {exc}") from exc

    if data.get("status") != 1 or "product" not in data:
        return None
    product = data["product"]
    product.setdefault("code", barcode)
    return _normalize(product)


def search_by_name(name, limit=5):
    """Return a list of normalized products matching a name."""
    if use_mock():
        term = name.lower()
        hits = [e for e in MOCK_OFF_DATABASE
                if term in e["product"]["product_name"].lower()
                or term in e["product"]["brands"].lower()]
        return [_normalize(_mock_to_raw(e)) for e in hits[:limit]]
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
    }
    try:
        resp = requests.get(
            f"{BASE_URL}/cgi/search.pl", params=params, headers=HEADERS, timeout=TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalAPIError(f"OpenFoodFacts request failed: {exc}") from exc

    return [_normalize(p) for p in data.get("products", [])]


def fetch_by_barcode_from_entry(entry):
    """Normalize one mock-database entry (used to seed the inventory)."""
    return _normalize(_mock_to_raw(entry))
