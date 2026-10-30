from decimal import Decimal

API = "/api/v1"


# ------------------------------------------------------------------ search


def test_search_returns_page_and_meta(client):
    r = client.get(f"{API}/products")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"] == {
        "page": 1, "page_size": 20, "total_items": 4, "total_pages": 1, "has_next": False, "has_prev": False,
    }
    assert {i["name"] for i in body["items"]} == {
        "iPhone 17 Pro 256GB Kozmik Turuncu", "Galaxy A18 128GB Açık Mavi", "iPhone 17 Pro Kılıfı", "USB-C Kablo",
    }


def test_search_text_matches_every_word_and_model(client):
    names = lambda r: [i["name"] for i in r.json()["items"]]  # noqa: E731
    assert names(client.get(f"{API}/products?q=iphone 17")) == ["iPhone 17 Pro 256GB Kozmik Turuncu", "iPhone 17 Pro Kılıfı"]
    assert names(client.get(f"{API}/products?q=turuncu iphone")) == ["iPhone 17 Pro 256GB Kozmik Turuncu"]
    assert names(client.get(f"{API}/products?q=MG8Q4TU")) == ["iPhone 17 Pro 256GB Kozmik Turuncu"]
    assert names(client.get(f"{API}/products?q=apple")) == ["iPhone 17 Pro 256GB Kozmik Turuncu", "USB-C Kablo"]
    assert names(client.get(f"{API}/products?q=nothing-here")) == []


def test_search_lowest_price_ignores_out_of_stock(client, ids):
    r = client.get(f"{API}/products?q=iphone 17 pro 256")
    item = r.json()["items"][0]
    assert item["product_id"] == ids["p_multi"]
    # Beymen (119999) is out of stock; Samsung (122679.38, stock unknown) counts.
    assert Decimal(item["lowest_price"]) == Decimal("122679.38")
    assert item["offer_count"] == 3 and item["retailer_count"] == 3
    assert item["brand"] == {"brand_id": ids["b_apple"], "name": "Apple"}
    assert item["category"]["category_id"] == ids["c_iphone"]


def test_search_product_without_offers_has_null_price(client, ids):
    r = client.get(f"{API}/products?q=kılıfı")
    item = r.json()["items"][0]
    assert item["product_id"] == ids["p_no_offers"]
    assert item["lowest_price"] is None and item["offer_count"] == 0


def test_search_sort_price(client):
    prices = lambda sort: [i["lowest_price"] for i in client.get(f"{API}/products?sort={sort}").json()["items"]]  # noqa: E731
    assert prices("price_asc") == ["399.00", "17999.00", "122679.38", None]
    assert prices("price_desc") == ["122679.38", "17999.00", "399.00", None]
    assert [i["name"] for i in client.get(f"{API}/products?sort=name_asc").json()["items"]][0] == "Galaxy A18 128GB Açık Mavi"


def test_search_relevance_prefers_multi_store_then_short_name(client):
    names = [i["name"] for i in client.get(f"{API}/products?q=iphone").json()["items"]]
    assert names == ["iPhone 17 Pro 256GB Kozmik Turuncu", "iPhone 17 Pro Kılıfı"]


def test_search_filters(client, ids):
    def total(qs):
        return client.get(f"{API}/products?{qs}").json()["meta"]["total_items"]

    assert total(f"category_id={ids['c_iphone']}") == 1
    assert total(f"category_id={ids['c_phones']}") == 2  # parent includes sub-category
    assert total(f"category_id={ids['c_acc']}") == 2
    assert total(f"brand_id={ids['b_apple']}") == 2
    assert total(f"retailer_id={ids['r_beymen']}") == 1
    assert total(f"retailer_id={ids['r_samsung']}") == 2
    assert total("min_price=1000&max_price=20000") == 1
    assert total("max_price=500") == 1
    assert total("in_stock=true") == 3
    assert total("in_stock=false") == 1


def test_search_pagination(client):
    r1 = client.get(f"{API}/products?sort=name_asc&page=1&page_size=3").json()
    r2 = client.get(f"{API}/products?sort=name_asc&page=2&page_size=3").json()
    assert r1["meta"]["total_pages"] == 2 and r1["meta"]["has_next"] and not r1["meta"]["has_prev"]
    assert len(r1["items"]) == 3 and len(r2["items"]) == 1
    assert r2["meta"]["has_prev"] and not r2["meta"]["has_next"]
    assert not {i["product_id"] for i in r1["items"]} & {i["product_id"] for i in r2["items"]}
    r3 = client.get(f"{API}/products?page=9").json()
    assert r3["items"] == [] and r3["meta"]["has_prev"] is True


def test_search_page_size_is_capped(client):
    assert client.get(f"{API}/products?page_size=5000").json()["meta"]["page_size"] == 100


def test_search_validation_errors(client):
    for qs in ("page=0", "page_size=0", "min_price=-1", "sort=cheapest", "category_id=abc"):
        r = client.get(f"{API}/products?{qs}")
        assert r.status_code == 422, qs
        err = r.json()["error"]
        assert err["code"] == "validation_error" and err["details"]

    r = client.get(f"{API}/products?min_price=10&max_price=5")
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "min_price"


# ----------------------------------------------------------------- detail


def test_product_detail_offers_sorted_and_lowest_flagged(client, ids):
    r = client.get(f"{API}/products/{ids['p_multi']}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "iPhone 17 Pro 256GB Kozmik Turuncu"
    assert body["model"] == "MG8Q4TU/A" and body["variant"] == "256 GB · Kozmik Turuncu"
    assert body["offer_count"] == 3 and body["retailer_count"] == 3
    assert Decimal(body["lowest_price"]) == Decimal("122679.38")

    offers = body["offers"]
    assert [o["price"] for o in offers] == ["119999.00", "122679.38", "125999.00"]
    assert [o["retailer"]["name"] for o in offers] == ["Beymen", "Samsung", "Pozitif Teknoloji"]
    assert [o["is_lowest"] for o in offers] == [False, True, False]
    assert offers[0]["in_stock"] is False and offers[1]["in_stock"] is None
    assert offers[0]["product_url"].startswith("https://www.beymen.com/")
    assert offers[0]["retailer_product_id"] == "1865304"
    assert offers[0]["currency"] == "TRY" and offers[0]["last_updated"]


def test_product_detail_without_offers(client, ids):
    body = client.get(f"{API}/products/{ids['p_no_offers']}").json()
    assert body["offers"] == [] and body["lowest_price"] is None and body["brand"] is None


def test_product_not_found(client):
    r = client.get(f"{API}/products/999999")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Product 999999 not found", "details": None}}


def test_product_id_must_be_positive_int(client):
    assert client.get(f"{API}/products/0").status_code == 422
    assert client.get(f"{API}/products/abc").status_code == 422


# ----------------------------------------------------------------- offers


def test_offers_endpoint(client, ids):
    r = client.get(f"{API}/products/{ids['p_multi']}/offers")
    assert r.status_code == 200
    assert [o["price"] for o in r.json()] == ["119999.00", "122679.38", "125999.00"]

    desc = client.get(f"{API}/products/{ids['p_multi']}/offers?sort=price_desc").json()
    assert [o["price"] for o in desc] == ["125999.00", "122679.38", "119999.00"]

    in_stock = client.get(f"{API}/products/{ids['p_multi']}/offers?in_stock_only=true").json()
    assert [o["retailer"]["name"] for o in in_stock] == ["Samsung", "Pozitif Teknoloji"]
    assert in_stock[0]["is_lowest"] is True

    assert client.get(f"{API}/products/{ids['p_no_offers']}/offers").json() == []
    assert client.get(f"{API}/products/424242/offers").status_code == 404


# ---------------------------------------------------------------- history


def test_history_default_window_and_ordering(client, ids):
    r = client.get(f"{API}/products/{ids['p_multi']}/history")
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == ids["p_multi"] and body["days"] == 30
    by_offer = {s["offer_id"]: s for s in body["series"]}
    assert len(by_offer) == 3 and {ids["o_pozitif"], ids["o_beymen"]} <= set(by_offer)
    pozitif = by_offer[ids["o_pozitif"]]
    assert pozitif["retailer"]["name"] == "Pozitif Teknoloji"
    assert [p["price"] for p in pozitif["points"]] == ["129999.00", "127999.00", "125999.00"]  # 100-day-old point excluded
    assert by_offer[ids["o_beymen"]]["points"] == []


def test_history_days_and_retailer_filters(client, ids):
    body = client.get(f"{API}/products/{ids['p_multi']}/history?days=365&retailer_id={ids['r_pozitif']}").json()
    assert len(body["series"]) == 1
    assert len(body["series"][0]["points"]) == 4

    assert client.get(f"{API}/products/{ids['p_multi']}/history?days=0").status_code == 422
    assert client.get(f"{API}/products/{ids['p_multi']}/history?days=400").status_code == 422
    assert client.get(f"{API}/products/{ids['p_no_offers']}/history").json()["series"] == []
    assert client.get(f"{API}/products/424242/history").status_code == 404
