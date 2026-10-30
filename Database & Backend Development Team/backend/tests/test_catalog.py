API = "/api/v1"


def test_categories_parents_first_with_counts(client, ids):
    r = client.get(f"{API}/categories")
    assert r.status_code == 200
    cats = {c["category_id"]: c for c in r.json()}
    assert cats[ids["c_phones"]]["parent_category_id"] is None
    assert cats[ids["c_iphone"]]["parent_category_id"] == ids["c_phones"]
    assert cats[ids["c_iphone"]]["product_count"] == 1
    assert cats[ids["c_phones"]]["product_count"] == 2  # own + sub-category
    assert cats[ids["c_acc"]]["product_count"] == 2
    assert r.json()[0]["parent_category_id"] is None


def test_brands(client, ids):
    brands = {b["name"]: b for b in client.get(f"{API}/brands").json()}
    assert brands["Apple"]["brand_id"] == ids["b_apple"] and brands["Apple"]["product_count"] == 2
    assert brands["Samsung"]["product_count"] == 1


def test_retailers(client, ids):
    retailers = {r["name"]: r for r in client.get(f"{API}/retailers").json()}
    assert retailers["Pozitif Teknoloji"]["offer_count"] == 2
    assert retailers["Samsung"]["offer_count"] == 2
    assert retailers["Beymen"]["offer_count"] == 1
    assert retailers["Beymen"]["website_url"] == "https://www.beymen.com"
