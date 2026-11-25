"""Simulated lab target (in-process, no network).

Identities:
  customer_a  — customer, owns order_1001, tenant tenant_a
  customer_b  — customer, owns order_1002, tenant tenant_b
  administrator — admin

Orders: order_1001 (customer_a, shipped), order_1002 (customer_b, paid).

Intentional vulnerabilities (lab only):
  (a) GET /api/orders/1001 as customer_b returns 200 (cross-user)
  (b) POST /api/admin/promote as a customer returns 200 (missing
      function-level authorisation)
  (c) POST /api/orders/1001/transition {"to_state": "created"} when the
      order is shipped returns 200 (invalid workflow transition accepted)

Correct controls: GET /api/admin/users as a customer returns 403, own
order returns 200, POST /api/orders as a customer returns 201, any
protected endpoint with session_valid=False returns 401, valid
transitions return 200, POST /api/admin/promote as administrator
returns 200 (legitimate).
"""

from copy import deepcopy

IDENTITIES = {
    "customer_a": {"identity": "customer_a", "role": "customer", "tenant": "tenant_a", "owns": ["order_1001"]},
    "customer_b": {"identity": "customer_b", "role": "customer", "tenant": "tenant_b", "owns": ["order_1002"]},
    "administrator": {"identity": "administrator", "role": "admin", "tenant": "tenant_a"},
}

_INITIAL_ORDERS = {
    "order_1001": {"id": "order_1001", "owner": "customer_a", "tenant": "tenant_a", "state": "shipped", "total": 49.99},
    "order_1002": {"id": "order_1002", "owner": "customer_b", "tenant": "tenant_b", "state": "paid", "total": 29.99},
}

ORDERS: dict = deepcopy(_INITIAL_ORDERS)

VALID_TRANSITIONS = {
    ("created", "paid"),
    ("paid", "shipped"),
}

PRODUCTS = [
    {"id": "prod_1", "name": "Apple Juice", "price": 1.99},
    {"id": "prod_2", "name": "Orange Juice", "price": 2.49},
]


def reset_orders() -> None:
    global ORDERS
    ORDERS = deepcopy(_INITIAL_ORDERS)


def _is_admin(identity: str) -> bool:
    return IDENTITIES.get(identity, {}).get("role") == "admin"


def handle(identity: str, method: str, path: str, body: dict | None = None, session_valid: bool = True) -> dict:
    """Handle one simulated request. Returns {"status": int, "body": dict}."""
    body = body or {}
    if identity not in IDENTITIES:
        return {"status": 401, "body": {"detail": "unknown identity"}}
    # Every endpoint in the inventory is protected.
    if not session_valid:
        return {"status": 401, "body": {"detail": "session expired or invalid"}}

    method = method.upper()
    parts = [p for p in path.strip("/").split("/") if p]

    # GET /api/products
    if method == "GET" and path == "/api/products":
        return {"status": 200, "body": {"products": deepcopy(PRODUCTS)}}

    # GET /api/orders
    if method == "GET" and path == "/api/orders":
        if _is_admin(identity):
            return {"status": 200, "body": {"orders": list(deepcopy(ORDERS).values())}}
        mine = [o for o in deepcopy(ORDERS).values() if o["owner"] == identity]
        return {"status": 200, "body": {"orders": mine}}

    # GET /api/orders/{id}  (path id "1001" maps to order "order_1001")
    if method == "GET" and len(parts) == 3 and parts[0] == "api" and parts[1] == "orders":
        order_id = parts[2] if parts[2].startswith("order_") else f"order_{parts[2]}"
        order = ORDERS.get(order_id)
        if order is None:
            return {"status": 404, "body": {"detail": "order not found"}}
        # VULN (a): cross-user access is not checked — any customer gets 200.
        return {"status": 200, "body": {"order": deepcopy(order)}}

    # POST /api/orders — persist the created order so its lifecycle
    # (e.g. created -> paid) can be exercised end-to-end through the target.
    # Transitions themselves are NOT persisted: the workflow invariant
    # reproduces shipped -> created twice and must see the same state.
    if method == "POST" and path == "/api/orders":
        order = {
            "id": "order_1003",
            "owner": identity,
            "tenant": IDENTITIES[identity]["tenant"],
            "state": "created",
            "total": body.get("total", 0),
        }
        ORDERS["order_1003"] = deepcopy(order)
        return {"status": 201, "body": {"order": deepcopy(order)}}

    # GET /api/profile
    if method == "GET" and path == "/api/profile":
        return {"status": 200, "body": {"profile": deepcopy(IDENTITIES[identity])}}

    # GET /api/admin/users
    if method == "GET" and path == "/api/admin/users":
        if not _is_admin(identity):
            return {"status": 403, "body": {"detail": "forbidden"}}
        return {"status": 200, "body": {"users": [deepcopy(v) for v in IDENTITIES.values()]}}

    # POST /api/admin/promote
    if method == "POST" and path == "/api/admin/promote":
        # VULN (b): missing function-level authorisation — customers get 200.
        return {"status": 200, "body": {"promoted": body.get("user", identity), "role": "admin"}}

    # POST /api/orders/{id}/transition
    if method == "POST" and len(parts) == 4 and parts[0] == "api" and parts[1] == "orders" and parts[3] == "transition":
        order_id = parts[2] if parts[2].startswith("order_") else f"order_{parts[2]}"
        order = ORDERS.get(order_id)
        if order is None:
            return {"status": 404, "body": {"detail": "order not found"}}
        to_state = body.get("to_state")
        current = order["state"]
        if (current, to_state) in VALID_TRANSITIONS:
            return {"status": 200, "body": {"order": {**deepcopy(order), "state": to_state}}}
        # VULN (c): shipped -> created is accepted.
        if current == "shipped" and to_state == "created":
            return {"status": 200, "body": {"order": {**deepcopy(order), "state": to_state}}}
        return {"status": 400, "body": {"detail": f"invalid transition {current} -> {to_state}"}}

    # POST /api/orders/{id}/total — CHALLENGE-ONLY scenario (CH-06).
    # The supplied total is accepted without validation and echoed back;
    # the tamper is NOT persisted (a copy is returned).
    if method == "POST" and len(parts) == 4 and parts[0] == "api" and parts[1] == "orders" and parts[3] == "total":
        order_id = parts[2] if parts[2].startswith("order_") else f"order_{parts[2]}"
        order = ORDERS.get(order_id)
        if order is None:
            return {"status": 404, "body": {"detail": "order not found"}}
        total = body.get("total")
        if not isinstance(total, (int, float)) or isinstance(total, bool):
            return {"status": 400, "body": {"detail": "total must be a number"}}
        tampered = deepcopy(order)
        tampered["total"] = total
        return {"status": 200, "body": {"order": tampered}}

    return {"status": 404, "body": {"detail": "not found"}}
