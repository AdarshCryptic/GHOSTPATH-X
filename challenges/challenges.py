"""Hands-on challenges for GHOSTPATH X v0.2 (lab only).

Six guided challenges mapped to the simulated lab target
(``lab.target.handle``). Solving never touches the main scan pipeline
and adds no new vulnerability to the scanned app — each challenge
re-runs one deterministic lab call and compares the observed status
with the expected one.

CH-04 is the exception that proves the control: it is solved when the
learner demonstrates the expired session *is* rejected (HTTP 401).
"""

from copy import deepcopy

from lab import target as lab_target

# ----------------------------------------------------------------------
# Public challenge data (what the API returns).
# ----------------------------------------------------------------------
CHALLENGES: list[dict] = [
    {
        "id": "CH-01",
        "title": "Cross-User Order Access",
        "difficulty": "Easy",
        "category": "Broken Object Level Authorization",
        "story": (
            "You are logged in as customer_b in the Juice Shop Training Lab. "
            "Your own order is order_1002 — but order URLs look predictable, "
            "just an ID in the path. What happens if you ask for somebody "
            "else's order?"
        ),
        "objective": (
            "Read order_1001, which belongs to customer_a, while "
            "authenticated as customer_b. The challenge is solved when the "
            "lab returns HTTP 200 for GET /api/orders/1001 as customer_b — "
            "proving the object-level authorization check is missing."
        ),
        "hints": [
            "Orders are addressed by ID in the URL: /api/orders/{id}.",
            "Try GET /api/orders/1001 while authenticated as customer_b.",
            "A 200 response containing customer_a's order means the lab "
            "never checked who owns the object — that is BOLA.",
        ],
        "lesson": (
            "Never trust an object ID from the URL. Every object access "
            "must be checked against the authenticated identity's ownership, "
            "server-side, on every request."
        ),
        "remediation": (
            "Enforce per-object ownership checks on GET /api/orders/{id}: "
            "return 403 when the order owner differs from the authenticated "
            "identity."
        ),
        "graph_path": ["Customer B", "Order API", "Order Resource", "Authorization Boundary"],
    },
    {
        "id": "CH-02",
        "title": "Admin Function Bypass",
        "difficulty": "Medium",
        "category": "Broken Function Level Authorization",
        "story": (
            "The lab has an admin endpoint, POST /api/admin/promote, that "
            "grants the admin role. The dashboard hides it from customers — "
            "but hidden is not the same as protected. Can a plain customer "
            "call it directly?"
        ),
        "objective": (
            "Call POST /api/admin/promote as customer_a. The challenge is "
            "solved when the lab returns HTTP 200 — proving the admin "
            "function has no role check."
        ),
        "hints": [
            "Admin functions live under /api/admin/ — the UI hides them, "
            "the API may not.",
            "Try POST /api/admin/promote as customer_a with a body such as "
            '{"user": "customer_a"}.',
            "A 200 response with role admin means the function-level check "
            "is missing — that is BFLA.",
        ],
        "lesson": (
            "Authorization must be enforced on the server for every "
            "function, not just hidden in the UI. Any client can call any "
            "endpoint it knows about."
        ),
        "remediation": (
            "Require the admin role on POST /api/admin/promote (and all "
            "/api/admin/* routes) before any state change; return 403 for "
            "non-admins."
        ),
        "graph_path": ["Customer A", "Admin API", "Promote Function", "Authorization Boundary"],
    },
    {
        "id": "CH-03",
        "title": "Invalid Workflow Transition",
        "difficulty": "Medium",
        "category": "Business Logic / Workflow",
        "story": (
            "Order_1001 has already shipped. The order lifecycle only allows "
            "created -> paid -> shipped, so a shipped order should never go "
            "back to created. But does the API actually enforce the state "
            "model, or does it trust whatever transition the client asks for?"
        ),
        "objective": (
            "Send POST /api/orders/1001/transition with "
            '{"to_state": "created"} as customer_a. The challenge is solved '
            "when the lab returns HTTP 200 for this invalid shipped -> "
            "created transition."
        ),
        "hints": [
            "Valid transitions are created -> paid and paid -> shipped only.",
            "Try POST /api/orders/1001/transition with "
            '{"to_state": "created"} as customer_a.',
            "A 200 response means the server accepted a transition the "
            "state model forbids — a business-logic flaw.",
        ],
        "lesson": (
            "State machines must be validated server-side. Clients can send "
            "any transition; only the server's state model decides what is "
            "legal."
        ),
        "remediation": (
            "Validate transitions server-side against the state model "
            "(created -> paid, paid -> shipped only); reject all others "
            "with 400."
        ),
        "graph_path": ["Customer A", "Order API", "Order Resource", "Workflow State Machine"],
    },
    {
        "id": "CH-04",
        "title": "Expired Session Reuse",
        "difficulty": "Easy",
        "category": "Session Management",
        "story": (
            "Sessions expire — or at least they should. In this challenge "
            "you play the defender: take an expired session and try to reuse "
            "it against a protected endpoint. A secure lab must refuse it."
        ),
        "objective": (
            "Demonstrate that the control WORKS: send GET /api/orders/1001 "
            "as customer_b with an expired session (session_valid=false). "
            "This challenge is solved when the lab correctly REJECTS the "
            "request with HTTP 401 — the session is not reusable. A 200 "
            "here would mean the session check is broken, not a solve."
        ),
        "hints": [
            "An expired session is submitted with session_valid=false.",
            "Try GET /api/orders/1001 as customer_b with session_valid=false.",
            "The solve is the rejection itself: HTTP 401 proves the "
            "session boundary holds.",
        ],
        "lesson": (
            "Every protected endpoint must re-validate the session on every "
            "request. Expiry is only real if the server enforces it — a 401 "
            "for an expired session is the control working as designed."
        ),
        "remediation": (
            "Keep the existing control: reject any request with an expired "
            "or invalid session with 401 before any authorization or "
            "business logic runs."
        ),
        "graph_path": ["Customer B", "Order API", "Session Boundary", "Authorization Boundary"],
    },
    {
        "id": "CH-05",
        "title": "Cross-Tenant Order Access",
        "difficulty": "Hard",
        "category": "Broken Object Level Authorization",
        "story": (
            "The lab is multi-tenant: customer_a lives in tenant_a, "
            "customer_b in tenant_b. Tenant isolation should be a hard "
            "boundary — one tenant's data must never leak to another. Test "
            "whether the order API respects the tenant line."
        ),
        "objective": (
            "Read order_1002, which belongs to customer_b in tenant_b, "
            "while authenticated as customer_a (tenant_a). The challenge is "
            "solved when the lab returns HTTP 200 for GET /api/orders/1002 "
            "as customer_a — proving tenant isolation is missing."
        ),
        "hints": [
            "customer_a is in tenant_a; order_1002 belongs to tenant_b.",
            "Try GET /api/orders/1002 while authenticated as customer_a.",
            "A 200 response across the tenant boundary means the API "
            "checks neither ownership nor tenancy.",
        ],
        "lesson": (
            "Multi-tenant apps must scope every query by tenant as well as "
            "by user. An ownership check alone is not enough if tenants "
            "share the same object store."
        ),
        "remediation": (
            "Scope all order queries by tenant: a request from tenant_a "
            "must never return an object owned by tenant_b; return 403 "
            "otherwise."
        ),
        "graph_path": ["Customer A", "Order API", "Order Resource", "Tenant Boundary"],
    },
    {
        "id": "CH-06",
        "title": "Product Price Tamper",
        "difficulty": "Hard",
        "category": "Business Logic / Parameter Tampering",
        "story": (
            "Order_1001 totals $49.99. The lab exposes an order-total "
            "endpoint that accepts a client-supplied total. If the server "
            "trusts that number, the price of an order is whatever the "
            "client says it is. Try it — as the wrong user, for good measure."
        ),
        "objective": (
            "Send POST /api/orders/1001/total with {\"total\": 0.01} as "
            "customer_b. The challenge is solved when the lab returns HTTP "
            "200 with the tampered total 0.01 — proving the server accepted "
            "a client-supplied price."
        ),
        "hints": [
            "The total endpoint is POST /api/orders/{id}/total with a "
            '{"total": <number>} body.',
            "Try POST /api/orders/1001/total with {\"total\": 0.01} as "
            "customer_b.",
            "A 200 response echoing total 0.01 means the price came from "
            "the client, not the catalogue — never trust client prices.",
        ],
        "lesson": (
            "Prices and totals must always be computed server-side from "
            "trusted data (catalogue prices, quantities). Any monetary value "
            "accepted from the client can be tampered with."
        ),
        "remediation": (
            "Never accept a client-supplied total: recompute order totals "
            "server-side from catalogue prices, and reject or ignore any "
            "total sent by the client."
        ),
        "graph_path": ["Customer B", "Order API", "Order Resource", "Pricing Logic"],
    },
]

# ----------------------------------------------------------------------
# Internal solve specs (not exposed through the API list/detail routes).
# ----------------------------------------------------------------------
_SOLVE_SPECS: dict[str, dict] = {
    "CH-01": {
        "identity": "customer_b",
        "method": "GET",
        "path": "/api/orders/1001",
        "body": {},
        "session_valid": True,
        "expected_status": 200,
    },
    "CH-02": {
        "identity": "customer_a",
        "method": "POST",
        "path": "/api/admin/promote",
        # No body enforced: the flaw is the missing role check, and the
        # lab accepts the call with any (or no) body.
        "body": {},
        "session_valid": True,
        "expected_status": 200,
    },
    "CH-03": {
        "identity": "customer_a",
        "method": "POST",
        "path": "/api/orders/1001/transition",
        "body": {"to_state": "created"},
        "session_valid": True,
        "expected_status": 200,
    },
    "CH-04": {
        "identity": "customer_b",
        "method": "GET",
        "path": "/api/orders/1001",
        "body": {},
        "session_valid": False,
        "expected_status": 401,
    },
    "CH-05": {
        "identity": "customer_a",
        "method": "GET",
        "path": "/api/orders/1002",
        "body": {},
        "session_valid": True,
        "expected_status": 200,
    },
    "CH-06": {
        "identity": "customer_b",
        "method": "POST",
        "path": "/api/orders/1001/total",
        "body": {"total": 0.01},
        "session_valid": True,
        "expected_status": 200,
    },
}

_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def list_challenges() -> list[dict]:
    """Public challenge dicts (deep copies; solve specs never included)."""
    return [deepcopy(c) for c in CHALLENGES]


def get_challenge(challenge_id: str) -> dict | None:
    for challenge in CHALLENGES:
        if challenge["id"] == challenge_id:
            return deepcopy(challenge)
    return None


def get_solve_spec(challenge_id: str) -> dict | None:
    spec = _SOLVE_SPECS.get(challenge_id)
    return deepcopy(spec) if spec is not None else None


def challenge_brief(challenge_id: str) -> str | None:
    """Markdown brief for the ``/brief`` download."""
    challenge = get_challenge(challenge_id)
    if challenge is None:
        return None
    hints = "\n".join(f"{i + 1}. {hint}" for i, hint in enumerate(challenge["hints"]))
    path = " -> ".join(challenge["graph_path"])
    return (
        f"# {challenge['id']} — {challenge['title']}\n\n"
        f"**Difficulty:** {challenge['difficulty']}  \n"
        f"**Category:** {challenge['category']}\n\n"
        f"## Story\n\n{challenge['story']}\n\n"
        f"## Objective\n\n{challenge['objective']}\n\n"
        f"## Hints\n\n{hints}\n\n"
        f"## Lesson\n\n{challenge['lesson']}\n\n"
        f"## Remediation\n\n{challenge['remediation']}\n\n"
        f"## Attack path\n\n{path}\n\n"
        f"_GHOSTPATH X — Autonomous Attack-Path Discovery & Exploit "
        f"Validation. Lab only: Juice Shop Training Lab (isolated lab)._ \n"
    )


def _bodies_match(submitted: dict, expected: dict) -> bool:
    """True when every expected body key matches the submitted value."""
    for key, value in expected.items():
        if key not in submitted:
            return False
        got = submitted[key]
        if isinstance(value, (int, float)) and isinstance(got, (int, float)):
            if float(got) != float(value):
                return False
        elif got != value:
            return False
    return True


def solve_challenge(
    challenge_id: str,
    identity: str,
    method: str,
    path: str,
    body: dict | None = None,
    session_valid: bool = True,
) -> dict:
    """Validate a solve attempt against the deterministic lab target.

    The submitted call is accepted only if it matches the challenge's
    expected method + path + identity (and expected body, when the
    challenge specifies one). The matching call is then executed against
    ``lab.target.handle`` and the observed status compared with the
    expected status. A non-matching call is still executed (for honest
    evidence) but can never solve the challenge.
    """
    spec = _SOLVE_SPECS.get(challenge_id)
    if spec is None:
        raise ValueError(f"unknown challenge: {challenge_id}")
    body = body or {}
    method = (method or "").upper()
    expected_status = spec["expected_status"]
    expected_str = (
        f"{spec['method']} {spec['path']} as {spec['identity']} "
        f"-> {expected_status}"
    )
    if challenge_id == "CH-04":
        expected_str += " (expired session correctly rejected)"

    matches = (
        method == spec["method"]
        and path == spec["path"]
        and identity == spec["identity"]
        and _bodies_match(body, spec["body"])
        and session_valid == spec["session_valid"]
    )

    resp = lab_target.handle(identity, method, path, body, session_valid=session_valid)
    status_code = resp["status"]
    observed = f"{status_code} for {method} {path} as {identity}"
    if challenge_id == "CH-06" and isinstance(resp.get("body"), dict):
        order = resp["body"].get("order") or {}
        if "total" in order:
            observed += f" (order total {order['total']})"

    solved = bool(matches and status_code == expected_status)
    if challenge_id == "CH-06" and solved:
        order = (resp.get("body") or {}).get("order") or {}
        solved = float(order.get("total", -1)) == float(spec["body"]["total"])

    if solved:
        if challenge_id == "CH-04":
            message = (
                "Challenge solved: the expired session was correctly "
                "rejected with HTTP 401 — the session boundary holds."
            )
        else:
            message = (
                f"Challenge solved: {method} {path} as {identity} "
                f"returned {status_code} as expected."
            )
    elif not matches:
        message = (
            "Not solved: the submitted call does not match the challenge's "
            f"expected call ({expected_str})."
        )
    else:
        message = (
            "Not solved: the call matched, but the lab returned "
            f"{status_code} instead of the expected {expected_status}."
        )

    return {
        "challenge_id": challenge_id,
        "solved": solved,
        "status": "solved" if solved else "failed",
        "evidence": {
            "expected": expected_str,
            "observed": observed,
            "status_code": status_code,
        },
        "message": message,
    }
