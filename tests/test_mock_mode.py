"""Tests for the mock OpenFoodFacts array, offline mode, seeding and enrich."""
import unittest
from unittest.mock import patch

from inventory import openfoodfacts as off
from inventory.app import create_app
from inventory.mock_data import MOCK_OFF_DATABASE, SEED_PRICING


class TestMockDatabaseShape(unittest.TestCase):
    def test_entries_resemble_openfoodfacts_response(self):
        for entry in MOCK_OFF_DATABASE:
            self.assertEqual(entry["status"], 1)
            self.assertIn("code", entry)
            for key in ("product_name", "brands", "ingredients_text"):
                self.assertTrue(entry["product"][key])

    def test_barcodes_unique_and_priced(self):
        codes = [e["code"] for e in MOCK_OFF_DATABASE]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(set(codes), set(SEED_PRICING))


@patch.dict("os.environ", {"OFF_USE_MOCK": "1"})
class TestOfflineMode(unittest.TestCase):
    def test_barcode_lookup(self):
        self.assertEqual(off.fetch_by_barcode("0000000000017")["brand"], "Silk")

    def test_barcode_not_found(self):
        self.assertIsNone(off.fetch_by_barcode("9999999999999"))

    def test_name_search_case_insensitive_and_by_brand(self):
        self.assertEqual(off.search_by_name("ALMOND")[0]["name"], "Organic Almond Milk")
        self.assertEqual(off.search_by_name("barilla")[0]["name"], "Whole Grain Spaghetti")

    def test_search_respects_limit(self):
        self.assertEqual(len(off.search_by_name("a", limit=2)), 2)

    @patch("inventory.openfoodfacts.requests.get")
    def test_no_network_used(self, mock_get):
        off.fetch_by_barcode("0000000000017")
        off.search_by_name("milk")
        mock_get.assert_not_called()


class TestSeeding(unittest.TestCase):
    def test_seeded_app_has_items_with_ids(self):
        client = create_app(seed=True).test_client()
        items = client.get("/inventory").get_json()
        self.assertEqual(len(items), len(MOCK_OFF_DATABASE))
        self.assertEqual([i["id"] for i in items], list(range(1, len(items) + 1)))
        self.assertTrue(all("price" in i and "stock" in i for i in items))

    def test_default_app_is_empty(self):
        self.assertEqual(create_app().test_client().get("/inventory").get_json(), [])

    def test_seeded_low_stock(self):
        client = create_app(seed=True).test_client()
        names = {i["name"] for i in client.get("/inventory/low-stock").get_json()}
        self.assertIn("Organic Almond Milk", names)


@patch.dict("os.environ", {"OFF_USE_MOCK": "1"})
class TestEnrich(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_enrich_fills_only_empty_fields(self):
        self.client.post("/inventory", json={
            "name": "My Almond Milk", "barcode": "0000000000017", "price": 9.99, "stock": 4})
        body = self.client.post("/inventory/1/enrich").get_json()
        self.assertEqual(body["name"], "My Almond Milk")   # kept
        self.assertEqual(body["price"], 9.99)               # kept
        self.assertEqual(body["brand"], "Silk")             # filled
        self.assertIn("almonds", body["ingredients"])       # filled

    def test_enrich_does_not_overwrite_existing(self):
        self.client.post("/inventory", json={
            "name": "X", "barcode": "0000000000017", "brand": "Store Brand"})
        self.assertEqual(self.client.post("/inventory/1/enrich").get_json()["brand"], "Store Brand")

    def test_enrich_missing_item_404(self):
        self.assertEqual(self.client.post("/inventory/9/enrich").status_code, 404)

    def test_enrich_without_barcode_400(self):
        self.client.post("/inventory", json={"name": "No code"})
        self.assertEqual(self.client.post("/inventory/1/enrich").status_code, 400)

    def test_enrich_unknown_barcode_404(self):
        self.client.post("/inventory", json={"name": "Ghost", "barcode": "1"})
        self.assertEqual(self.client.post("/inventory/1/enrich").status_code, 404)

    def test_enrich_upstream_failure_502(self):
        self.client.post("/inventory", json={"name": "X", "barcode": "1"})
        with patch("inventory.app.off.fetch_by_barcode",
                   side_effect=off.ExternalAPIError("down")):
            self.assertEqual(self.client.post("/inventory/1/enrich").status_code, 502)


if __name__ == "__main__":
    unittest.main()
