"""Discovery tests — discovery/api_inventory.py + discovery/crawler.py.

Contract: the endpoint inventory has 8 unique endpoints; dedup is by
method + path, so adding the same endpoint twice does not duplicate it.
"""

from discovery.api_inventory import ENDPOINTS, get_inventory
from discovery.crawler import Crawler, dedupe_endpoints

EXPECTED_ENDPOINTS = {
    ("GET", "/api/products"),
    ("GET", "/api/orders"),
    ("GET", "/api/orders/{id}"),
    ("POST", "/api/orders"),
    ("GET", "/api/profile"),
    ("GET", "/api/admin/users"),
    ("POST", "/api/admin/promote"),
    ("POST", "/api/orders/{id}/transition"),
}


def _keys(endpoints):
    return {(e["method"], e["path"]) for e in endpoints}


def test_endpoint_inventory_has_8_unique_endpoints():
    inventory = get_inventory()
    assert len(inventory) == 8, f"expected 8 endpoints, got {len(inventory)}: {inventory}"
    assert _keys(inventory) == EXPECTED_ENDPOINTS
    assert len(_keys(inventory)) == 8, "inventory must contain 8 unique method+path pairs"
    # The module-level constant and the getter agree.
    assert _keys(ENDPOINTS) == EXPECTED_ENDPOINTS


def test_dedup_by_method_and_path():
    inventory = get_inventory()
    # Adding the same endpoint twice (even three times) does not duplicate it.
    doubled = inventory + [inventory[0], inventory[0], inventory[3]]
    deduped = dedupe_endpoints(doubled)
    assert len(deduped) == 8
    assert _keys(deduped) == EXPECTED_ENDPOINTS
    # Same path with a different method is a different endpoint.
    assert len(dedupe_endpoints([
        {"method": "GET", "path": "/api/orders"},
        {"method": "POST", "path": "/api/orders"},
    ])) == 2
    # Exact duplicate collapses to one.
    assert len(dedupe_endpoints([
        {"method": "GET", "path": "/api/orders"},
        {"method": "GET", "path": "/api/orders"},
    ])) == 1


def test_crawler_returns_deduped_inventory():
    endpoints = Crawler().crawl()
    assert len(endpoints) == 8
    assert _keys(endpoints) == EXPECTED_ENDPOINTS
