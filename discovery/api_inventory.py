"""Endpoint inventory for the simulated lab (8 endpoints)."""

ENDPOINTS = [
    {"method": "GET", "path": "/api/products", "auth": True},
    {"method": "GET", "path": "/api/orders", "auth": True},
    {"method": "GET", "path": "/api/orders/{id}", "auth": True},
    {"method": "POST", "path": "/api/orders", "auth": True},
    {"method": "GET", "path": "/api/profile", "auth": True},
    {"method": "GET", "path": "/api/admin/users", "auth": True},
    {"method": "POST", "path": "/api/admin/promote", "auth": True},
    {"method": "POST", "path": "/api/orders/{id}/transition", "auth": True},
]


def get_inventory() -> list[dict]:
    return [dict(e) for e in ENDPOINTS]
