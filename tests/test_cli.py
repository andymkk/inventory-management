"""Tests for the CLI (the HTTP layer is mocked)."""
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

import requests

from inventory import cli


def fake_response(body, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    return resp


def run_cli(argv, response=None, side_effect=None):
    """Run the CLI, returning (exit_code, stdout, stderr, mock_request)."""
    out, err = io.StringIO(), io.StringIO()
    with patch("inventory.cli.requests.request") as mock_req, \
            redirect_stdout(out), redirect_stderr(err):
        if side_effect:
            mock_req.side_effect = side_effect
        else:
            mock_req.return_value = response
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue(), mock_req


class TestCLI(unittest.TestCase):
    def test_list(self):
        code, out, _, req = run_cli(["list"], fake_response([{"id": 1, "name": "Milk"}]))
        self.assertEqual(code, 0)
        self.assertIn("Milk", out)
        self.assertEqual(req.call_args.args[0], "GET")
        self.assertTrue(req.call_args.args[1].endswith("/inventory"))

    def test_list_with_search(self):
        _, _, _, req = run_cli(["list", "--search", "oat"], fake_response([]))
        self.assertEqual(req.call_args.kwargs["params"], {"q": "oat"})

    def test_get(self):
        code, out, _, req = run_cli(["get", "3"], fake_response({"id": 3}))
        self.assertEqual(code, 0)
        self.assertTrue(req.call_args.args[1].endswith("/inventory/3"))

    def test_add_sends_post_body(self):
        _, _, _, req = run_cli(["add", "Rice", "--price", "2.5", "--stock", "9"],
                               fake_response({"id": 1}, 201))
        self.assertEqual(req.call_args.args[0], "POST")
        body = req.call_args.kwargs["json"]
        self.assertEqual((body["name"], body["price"], body["stock"]), ("Rice", 2.5, 9))

    def test_update_sends_only_given_fields(self):
        _, _, _, req = run_cli(["update", "1", "--stock", "4"], fake_response({"id": 1}))
        self.assertEqual(req.call_args.args[0], "PATCH")
        self.assertEqual(req.call_args.kwargs["json"], {"stock": 4})

    def test_update_with_no_fields_fails_without_request(self):
        code, _, err, req = run_cli(["update", "1"], fake_response({}))
        self.assertEqual(code, 1)
        self.assertIn("Nothing to update", err)
        req.assert_not_called()

    def test_delete(self):
        code, out, _, req = run_cli(["delete", "2"], fake_response({"message": "gone"}))
        self.assertEqual(code, 0)
        self.assertEqual(req.call_args.args[0], "DELETE")

    def test_low_stock(self):
        _, _, _, req = run_cli(["low-stock", "--threshold", "8"], fake_response([]))
        self.assertEqual(req.call_args.kwargs["params"], {"threshold": 8})

    def test_lookup_by_barcode(self):
        _, _, _, req = run_cli(["lookup", "--barcode", "123"], fake_response({"name": "X"}))
        self.assertTrue(req.call_args.args[1].endswith("/external/barcode/123"))

    def test_lookup_by_name(self):
        _, _, _, req = run_cli(["lookup", "--name", "milk"], fake_response([]))
        self.assertTrue(req.call_args.args[1].endswith("/external/search"))
        self.assertEqual(req.call_args.kwargs["params"], {"name": "milk"})

    def test_import_by_barcode(self):
        _, _, _, req = run_cli(
            ["import", "--barcode", "123", "--price", "4.99", "--stock", "12"],
            fake_response({"id": 1}, 201))
        self.assertTrue(req.call_args.args[1].endswith("/inventory/import"))
        self.assertEqual(req.call_args.kwargs["json"],
                         {"price": 4.99, "stock": 12, "barcode": "123"})

    def test_import_by_name(self):
        _, _, _, req = run_cli(["import", "--name", "nutella"], fake_response({"id": 1}, 201))
        self.assertEqual(req.call_args.kwargs["json"]["name"], "nutella")

    def test_api_error_prints_message_and_returns_1(self):
        code, _, err, _ = run_cli(["get", "9"], fake_response({"error": "Item not found."}, 404))
        self.assertEqual(code, 1)
        self.assertIn("Item not found.", err)

    def test_server_down_is_handled(self):
        code, _, err, _ = run_cli(["list"], side_effect=requests.ConnectionError())
        self.assertEqual(code, 1)
        self.assertIn("Could not connect", err)

    def test_lookup_requires_barcode_or_name(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(["lookup"])


if __name__ == "__main__":
    unittest.main()


class TestEnrichAndMenu(unittest.TestCase):
    def test_enrich_command(self):
        _, _, _, req = run_cli(["enrich", "2"], fake_response({"id": 2}))
        self.assertEqual(req.call_args.args[0], "POST")
        self.assertTrue(req.call_args.args[1].endswith("/inventory/2/enrich"))

    def _run_menu(self, inputs, response=None):
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), \
                patch("inventory.cli.requests.request") as req, \
                redirect_stdout(out), redirect_stderr(io.StringIO()):
            req.return_value = response or fake_response({"ok": True})
            code = cli.main(["menu"])
        return code, out.getvalue(), req

    def test_menu_quit(self):
        code, out, req = self._run_menu(["0"])
        self.assertEqual(code, 0)
        self.assertIn("Goodbye", out)
        req.assert_not_called()

    def test_menu_view_all(self):
        _, _, req = self._run_menu(["1", "0"])
        self.assertEqual(req.call_args.args[0], "GET")

    def test_menu_add_item(self):
        _, _, req = self._run_menu(["3", "Rice", "2.5", "9", "0"], fake_response({"id": 1}, 201))
        body = req.call_args.kwargs["json"]
        self.assertEqual((body["name"], body["price"], body["stock"]), ("Rice", 2.5, 9))

    def test_menu_update_skips_blank_fields(self):
        _, _, req = self._run_menu(["4", "1", "", "7", "0"])
        self.assertEqual(req.call_args.kwargs["json"], {"stock": 7})

    def test_menu_reprompts_on_invalid_number(self):
        _, out, req = self._run_menu(["2", "abc", "3", "0"])
        self.assertIn("Invalid input", out)
        self.assertTrue(req.call_args.args[1].endswith("/inventory/3"))

    def test_menu_unknown_option(self):
        _, out, _ = self._run_menu(["42", "0"])
        self.assertIn("Unknown option", out)

    def test_menu_import_by_barcode(self):
        _, _, req = self._run_menu(["7", "b", "123", "4.99", "12", "0"], fake_response({"id": 1}, 201))
        self.assertEqual(req.call_args.kwargs["json"],
                         {"price": 4.99, "stock": 12, "barcode": "123"})
