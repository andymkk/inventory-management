"""Tests for the OpenFoodFacts client (HTTP is mocked)."""
import unittest
from unittest.mock import MagicMock, patch

import requests

from inventory import openfoodfacts as off

RAW = {
    "code": "123",
    "product_name": "Nutella",
    "brands": "Ferrero",
    "categories": "Spreads, Sweet spreads",
    "ingredients_text": "Sugar, palm oil",
    "quantity": "400 g",
    "image_url": "http://img/x.jpg",
}


def fake_response(json_data=None, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    if status >= 400 and status != 404:
        resp.raise_for_status.side_effect = requests.HTTPError("boom")
    return resp


@patch("inventory.openfoodfacts.requests.get")
class TestBarcode(unittest.TestCase):
    def test_found(self, mock_get):
        mock_get.return_value = fake_response({"status": 1, "product": dict(RAW)})
        product = off.fetch_by_barcode("123")
        self.assertEqual(product["name"], "Nutella")
        self.assertEqual(product["brand"], "Ferrero")
        self.assertEqual(product["category"], "Spreads")
        self.assertEqual(product["barcode"], "123")

    def test_not_found_status_zero(self, mock_get):
        mock_get.return_value = fake_response({"status": 0})
        self.assertIsNone(off.fetch_by_barcode("000"))

    def test_not_found_404(self, mock_get):
        mock_get.return_value = fake_response({}, status=404)
        self.assertIsNone(off.fetch_by_barcode("000"))

    def test_network_error_raises(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("down")
        with self.assertRaises(off.ExternalAPIError):
            off.fetch_by_barcode("123")

    def test_server_error_raises(self, mock_get):
        mock_get.return_value = fake_response({}, status=500)
        with self.assertRaises(off.ExternalAPIError):
            off.fetch_by_barcode("123")

    def test_missing_name_gets_placeholder(self, mock_get):
        mock_get.return_value = fake_response({"status": 1, "product": {"code": "1"}})
        self.assertEqual(off.fetch_by_barcode("1")["name"], "Unknown product")


@patch("inventory.openfoodfacts.requests.get")
class TestSearch(unittest.TestCase):
    def test_returns_normalized_list(self, mock_get):
        mock_get.return_value = fake_response({"products": [RAW, RAW]})
        results = off.search_by_name("nutella")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Nutella")

    def test_passes_search_term_and_limit(self, mock_get):
        mock_get.return_value = fake_response({"products": []})
        off.search_by_name("milk", limit=3)
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["search_terms"], "milk")
        self.assertEqual(params["page_size"], 3)

    def test_empty_results(self, mock_get):
        mock_get.return_value = fake_response({"products": []})
        self.assertEqual(off.search_by_name("zzzz"), [])

    def test_network_error_raises(self, mock_get):
        mock_get.side_effect = requests.Timeout("slow")
        with self.assertRaises(off.ExternalAPIError):
            off.search_by_name("milk")


if __name__ == "__main__":
    unittest.main()
