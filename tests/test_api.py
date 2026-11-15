"""Tests for the Flask CRUD routes and helper routes."""
import unittest

from inventory.app import create_app


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def create(self, **overrides):
        payload = {"name": "Oat Milk", "brand": "Oatly", "price": 3.5, "stock": 10}
        payload.update(overrides)
        return self.client.post("/inventory", json=payload)


class TestCreate(APITestCase):
    def test_create_returns_201_and_item(self):
        resp = self.create()
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(body["id"], 1)
        self.assertEqual(body["name"], "Oat Milk")

    def test_ids_increment(self):
        self.create()
        self.assertEqual(self.create(name="Rice").get_json()["id"], 2)

    def test_defaults_are_applied(self):
        body = self.client.post("/inventory", json={"name": "Salt"}).get_json()
        self.assertEqual(body["stock"], 0)
        self.assertEqual(body["price"], 0.0)

    def test_missing_name_is_400(self):
        resp = self.client.post("/inventory", json={"price": 1})
        self.assertEqual(resp.status_code, 400)

    def test_negative_price_is_400(self):
        self.assertEqual(self.create(price=-1).status_code, 400)

    def test_non_integer_stock_is_400(self):
        self.assertEqual(self.create(stock="lots").status_code, 400)

    def test_unknown_field_is_400(self):
        self.assertEqual(self.create(color="red").status_code, 400)

    def test_non_json_body_is_400(self):
        resp = self.client.post("/inventory", data="not json")
        self.assertEqual(resp.status_code, 400)


class TestRead(APITestCase):
    def test_list_empty(self):
        resp = self.client.get("/inventory")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    def test_list_returns_all(self):
        self.create()
        self.create(name="Rice")
        self.assertEqual(len(self.client.get("/inventory").get_json()), 2)

    def test_search_filter(self):
        self.create()
        self.create(name="Rice", brand="Uncle Ben's")
        resp = self.client.get("/inventory?q=oat")
        self.assertEqual([i["name"] for i in resp.get_json()], ["Oat Milk"])

    def test_get_one(self):
        self.create()
        resp = self.client.get("/inventory/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["name"], "Oat Milk")

    def test_get_missing_is_404(self):
        self.assertEqual(self.client.get("/inventory/99").status_code, 404)


class TestUpdate(APITestCase):
    def test_patch_updates_only_given_fields(self):
        self.create()
        resp = self.client.patch("/inventory/1", json={"stock": 3})
        body = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["stock"], 3)
        self.assertEqual(body["name"], "Oat Milk")

    def test_patch_persists(self):
        self.create()
        self.client.patch("/inventory/1", json={"price": 9.99})
        self.assertEqual(self.client.get("/inventory/1").get_json()["price"], 9.99)

    def test_patch_missing_is_404(self):
        self.assertEqual(self.client.patch("/inventory/5", json={"stock": 1}).status_code, 404)

    def test_patch_invalid_is_400(self):
        self.create()
        self.assertEqual(self.client.patch("/inventory/1", json={"stock": -2}).status_code, 400)

    def test_patch_cannot_change_id(self):
        self.create()
        self.assertEqual(self.client.patch("/inventory/1", json={"id": 7}).status_code, 400)


class TestDelete(APITestCase):
    def test_delete_removes_item(self):
        self.create()
        self.assertEqual(self.client.delete("/inventory/1").status_code, 200)
        self.assertEqual(self.client.get("/inventory/1").status_code, 404)

    def test_delete_missing_is_404(self):
        self.assertEqual(self.client.delete("/inventory/1").status_code, 404)

    def test_ids_not_reused_after_delete(self):
        self.create()
        self.client.delete("/inventory/1")
        self.assertEqual(self.create().get_json()["id"], 2)


class TestHelperRoutes(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})

    def test_low_stock_default_threshold(self):
        self.create(name="Low", stock=2)
        self.create(name="Plenty", stock=50)
        names = [i["name"] for i in self.client.get("/inventory/low-stock").get_json()]
        self.assertEqual(names, ["Low"])

    def test_low_stock_custom_threshold(self):
        self.create(name="A", stock=10)
        resp = self.client.get("/inventory/low-stock?threshold=10")
        self.assertEqual(len(resp.get_json()), 1)


if __name__ == "__main__":
    unittest.main()
