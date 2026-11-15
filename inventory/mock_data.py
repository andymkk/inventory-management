"""Mock OpenFoodFacts database (an array), used to seed the inventory and to
run the app offline.

Each entry mirrors the shape of a real OpenFoodFacts response:
    {"status": 1, "product": {"product_name": ..., "brands": ..., ...}}
plus a "code" (barcode) so we can look entries up like the real API does.
Barcodes other than Nutella's are made up for this lab.
"""

MOCK_OFF_DATABASE = [
    {
        "code": "3017620422003", "status": 1,
        "product": {
            "product_name": "Nutella", "brands": "Ferrero",
            "categories": "Spreads, Sweet spreads, Hazelnut spreads",
            "ingredients_text": "Sugar, palm oil, hazelnuts 13%, skimmed milk powder 8.7%, cocoa 7.4%, lecithin, vanillin",
            "quantity": "400 g", "image_url": "",
        },
    },
    {
        "code": "0000000000017", "status": 1,
        "product": {
            "product_name": "Organic Almond Milk", "brands": "Silk",
            "categories": "Plant-based milks, Almond milks",
            "ingredients_text": "Filtered water, almonds, cane sugar, sea salt, sunflower lecithin",
            "quantity": "1 L", "image_url": "",
        },
    },
    {
        "code": "0000000000024", "status": 1,
        "product": {
            "product_name": "Oat Drink Barista", "brands": "Oatly",
            "categories": "Plant-based milks, Oat milks",
            "ingredients_text": "Water, oats 10%, rapeseed oil, calcium carbonate, salt",
            "quantity": "1 L", "image_url": "",
        },
    },
    {
        "code": "0000000000031", "status": 1,
        "product": {
            "product_name": "Whole Grain Spaghetti", "brands": "Barilla",
            "categories": "Pastas, Whole grain pastas",
            "ingredients_text": "Whole durum wheat semolina, water",
            "quantity": "500 g", "image_url": "",
        },
    },
    {
        "code": "0000000000048", "status": 1,
        "product": {
            "product_name": "Crunchy Peanut Butter", "brands": "Skippy",
            "categories": "Spreads, Peanut butters",
            "ingredients_text": "Roasted peanuts, sugar, hydrogenated vegetable oil, salt",
            "quantity": "340 g", "image_url": "",
        },
    },
    {
        "code": "0000000000055", "status": 1,
        "product": {
            "product_name": "Dark Chocolate 70%", "brands": "Lindt",
            "categories": "Snacks, Chocolates, Dark chocolates",
            "ingredients_text": "Cocoa mass, sugar, cocoa butter, vanilla",
            "quantity": "100 g", "image_url": "",
        },
    },
    {
        "code": "0000000000062", "status": 1,
        "product": {
            "product_name": "Basmati Rice", "brands": "Tilda",
            "categories": "Cereals and potatoes, Rice, Basmati rices",
            "ingredients_text": "Basmati rice",
            "quantity": "1 kg", "image_url": "",
        },
    },
    {
        "code": "0000000000079", "status": 1,
        "product": {
            "product_name": "Orange Juice", "brands": "Tropicana",
            "categories": "Beverages, Fruit juices, Orange juices",
            "ingredients_text": "Orange juice from concentrate",
            "quantity": "900 ml", "image_url": "",
        },
    },
]

# Our own bookkeeping for seeded items: barcode -> (price, stock).
# OpenFoodFacts doesn't know prices or how many units we hold.
SEED_PRICING = {
    "3017620422003": (4.99, 24),
    "0000000000017": (3.49, 3),
    "0000000000024": (3.99, 18),
    "0000000000031": (1.89, 40),
    "0000000000048": (3.25, 2),
    "0000000000055": (2.79, 31),
    "0000000000062": (5.50, 12),
    "0000000000079": (2.99, 9),
}
