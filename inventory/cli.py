"""Command-line interface that talks to the Flask inventory API.

Usage examples:
    python -m inventory.cli list
    python -m inventory.cli add "Oat Milk" --price 3.5 --stock 20
    python -m inventory.cli lookup --barcode 3017620422003
    python -m inventory.cli import --barcode 3017620422003 --price 4.99 --stock 12
    python -m inventory.cli menu        # interactive menu
"""
import argparse
import json
import os
import sys

import requests

API_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


def call_api(method, path, **kwargs):
    """Send a request to the API and return (status_code, parsed_json)."""
    try:
        resp = requests.request(method, f"{API_URL}{path}", timeout=15, **kwargs)
    except requests.ConnectionError:
        print(f"Could not connect to the API at {API_URL}. Is the server running?",
              file=sys.stderr)
        return None, None
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, None


def show(status, body, success_codes=(200, 201)):
    """Pretty-print a response. Returns a process exit code."""
    if status is None:
        return 1
    if status in success_codes:
        print(json.dumps(body, indent=2))
        return 0
    message = body.get("error") if isinstance(body, dict) else None
    print(f"Error {status}: {message or 'request failed'}", file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(description="Inventory management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List all items")
    p.add_argument("--search", help="Filter by name or brand")

    p = sub.add_parser("get", help="Show one item")
    p.add_argument("id", type=int)

    p = sub.add_parser("add", help="Add an item manually")
    p.add_argument("name")
    p.add_argument("--brand", default="")
    p.add_argument("--barcode", default="")
    p.add_argument("--category", default="")
    p.add_argument("--price", type=float, default=0.0)
    p.add_argument("--stock", type=int, default=0)

    p = sub.add_parser("update", help="Update fields of an item")
    p.add_argument("id", type=int)
    p.add_argument("--name")
    p.add_argument("--brand")
    p.add_argument("--category")
    p.add_argument("--price", type=float)
    p.add_argument("--stock", type=int)

    p = sub.add_parser("delete", help="Delete an item")
    p.add_argument("id", type=int)

    p = sub.add_parser("low-stock", help="List items at or below a stock threshold")
    p.add_argument("--threshold", type=int, default=5)

    p = sub.add_parser("lookup", help="Look up a product on OpenFoodFacts")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--barcode")
    g.add_argument("--name")

    p = sub.add_parser("enrich", help="Fill an item's empty fields from OpenFoodFacts")
    p.add_argument("id", type=int)

    sub.add_parser("menu", help="Interactive menu")

    p = sub.add_parser("import", help="Fetch from OpenFoodFacts and add to inventory")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--barcode")
    g.add_argument("--name")
    p.add_argument("--price", type=float, default=0.0)
    p.add_argument("--stock", type=int, default=0)

    return parser


def run(args):
    cmd = args.command
    if cmd == "list":
        params = {"q": args.search} if args.search else None
        return show(*call_api("GET", "/inventory", params=params))
    if cmd == "get":
        return show(*call_api("GET", f"/inventory/{args.id}"))
    if cmd == "add":
        body = {k: getattr(args, k) for k in
                ("name", "brand", "barcode", "category", "price", "stock")}
        return show(*call_api("POST", "/inventory", json=body))
    if cmd == "update":
        body = {k: getattr(args, k) for k in
                ("name", "brand", "category", "price", "stock")
                if getattr(args, k) is not None}
        if not body:
            print("Nothing to update. Pass at least one field.", file=sys.stderr)
            return 1
        return show(*call_api("PATCH", f"/inventory/{args.id}", json=body))
    if cmd == "delete":
        return show(*call_api("DELETE", f"/inventory/{args.id}"))
    if cmd == "low-stock":
        return show(*call_api("GET", "/inventory/low-stock",
                              params={"threshold": args.threshold}))
    if cmd == "lookup":
        if args.barcode:
            return show(*call_api("GET", f"/external/barcode/{args.barcode}"))
        return show(*call_api("GET", "/external/search", params={"name": args.name}))
    if cmd == "enrich":
        return show(*call_api("POST", f"/inventory/{args.id}/enrich"))
    if cmd == "menu":
        return menu()
    if cmd == "import":
        body = {"price": args.price, "stock": args.stock}
        body["barcode" if args.barcode else "name"] = args.barcode or args.name
        return show(*call_api("POST", "/inventory/import", json=body))
    return 1


MENU = """
===== Inventory Manager =====
 1) View all items          5) Delete an item
 2) View one item           6) Find product on OpenFoodFacts
 3) Add an item             7) Import product from OpenFoodFacts
 4) Update price / stock    8) Enrich an item from OpenFoodFacts
 9) Low-stock report        0) Quit
"""


def _ask(prompt, cast=str, required=True):
    """Prompt until the input converts with `cast` (blank allowed if not required)."""
    while True:
        raw = input(prompt).strip()
        if not raw and not required:
            return None
        try:
            if raw:
                return cast(raw)
        except ValueError:
            print("Invalid input, please try again.")
            continue
        print("This field is required.")


def menu():
    """Menu-driven front end: each choice builds argv and reuses main()."""
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            return 0
        if choice == "1":
            main(["list"])
        elif choice == "2":
            main(["get", str(_ask("Item id: ", int))])
        elif choice == "3":
            argv = ["add", _ask("Name: "),
                    "--price", str(_ask("Price: ", float)),
                    "--stock", str(_ask("Stock: ", int))]
            main(argv)
        elif choice == "4":
            argv = ["update", str(_ask("Item id: ", int))]
            price = _ask("New price (blank to skip): ", float, required=False)
            stock = _ask("New stock (blank to skip): ", int, required=False)
            if price is not None:
                argv += ["--price", str(price)]
            if stock is not None:
                argv += ["--stock", str(stock)]
            main(argv)
        elif choice == "5":
            main(["delete", str(_ask("Item id: ", int))])
        elif choice == "6":
            kind = _ask("Search by (b)arcode or (n)ame? ")
            flag = "--barcode" if kind.lower().startswith("b") else "--name"
            main(["lookup", flag, _ask("Value: ")])
        elif choice == "7":
            kind = _ask("Import by (b)arcode or (n)ame? ")
            flag = "--barcode" if kind.lower().startswith("b") else "--name"
            main(["import", flag, _ask("Value: "),
                  "--price", str(_ask("Price: ", float)),
                  "--stock", str(_ask("Stock: ", int))])
        elif choice == "8":
            main(["enrich", str(_ask("Item id: ", int))])
        elif choice == "9":
            main(["low-stock"])
        else:
            print("Unknown option.")


def main(argv=None):
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
