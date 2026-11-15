"""Tests for routes that integrate the external API with the inventory."""
import unittest
from unittest.mock import patch

from inventory.app import create_app
from inventory.openfoodfacts import ExternalAPIError

PRODUCT = {
    "name": "Nutella", "brand": "Ferrero", "barcode": "123",
    "category": "Spreads", "ingredients": "Sugar",
    "quantity_label": "400 g", "image_url": "",
}


class ExternalRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()


@patch("inventory.app.off.fetch_by_barcode")
class TestBarcodeRoute(ExternalRouteTestCase):
    def test_found(self, mock_fetch):
        mock_fetch.return_value = dict(PRODUCT)
        resp = self.client.get("/external/barcode/123")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["name"], "Nutella")

    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = None
        self.assertEqual(self.client.get("/external/barcode/0").status_code, 404)

    def test_upstream_failure_is_502(self, mock_fetch):
        mock_fetch.side_effect = ExternalAPIError("down")
        self.assertEqual(self.client.get("/external/barcode/1").status_code, 502)


@patch("inventory.app.off.search_by_name")
class TestSearchRoute(ExternalRouteTestCase):
    def test_search(self, mock_search):
        mock_search.return_value = [dict(PRODUCT)]
        resp = self.client.get("/external/search?name=nutella")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 1)

    def test_missing_name_is_400(self, mock_search):
        self.assertEqual(self.client.get("/external/search").status_code, 400)
        mock_search.assert_not_called()

    def test_upstream_failure_is_502(self, mock_search):
        mock_search.side_effect = ExternalAPIError("down")
        self.assertEqual(self.client.get("/external/search?name=x").status_code, 502)


class TestImportRoute(ExternalRouteTestCase):
    @patch("inventory.app.off.fetch_by_barcode")
    def test_import_by_barcode_adds_to_inventory(self, mock_fetch):
        mock_fetch.return_value = dict(PRODUCT)
        resp = self.client.post("/inventory/import",
                                json={"barcode": "123", "price": 4.99, "stock": 12})
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(body["name"], "Nutella")
        self.assertEqual(body["price"], 4.99)
        self.assertEqual(body["stock"], 12)
        # Item really landed in the inventory array
        self.assertEqual(len(self.client.get("/inventory").get_json()), 1)

    @patch("inventory.app.off.search_by_name")
    def test_import_by_name_uses_first_result(self, mock_search):
        mock_search.return_value = [dict(PRODUCT), {**PRODUCT, "name": "Other"}]
        resp = self.client.post("/inventory/import", json={"name": "nutella"})
        self.assertEqual(resp.get_json()["name"], "Nutella")

    @patch("inventory.app.off.fetch_by_barcode")
    def test_import_not_found_is_404_and_adds_nothing(self, mock_fetch):
        mock_fetch.return_value = None
        resp = self.client.post("/inventory/import", json={"barcode": "0"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.client.get("/inventory").get_json(), [])

    def test_import_requires_barcode_or_name(self):
        self.assertEqual(self.client.post("/inventory/import", json={}).status_code, 400)

    def test_import_validates_stock(self):
        resp = self.client.post("/inventory/import", json={"barcode": "1", "stock": -5})
        self.assertEqual(resp.status_code, 400)

    @patch("inventory.app.off.fetch_by_barcode")
    def test_import_upstream_failure_is_502(self, mock_fetch):
        mock_fetch.side_effect = ExternalAPIError("down")
        resp = self.client.post("/inventory/import", json={"barcode": "1"})
        self.assertEqual(resp.status_code, 502)


if __name__ == "__main__":
    unittest.main()
