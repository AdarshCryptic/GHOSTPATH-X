"""Role registry for the 3 lab identities."""

from lab.target import IDENTITIES

ROLES = {
    "customer_a": "customer",
    "customer_b": "customer",
    "administrator": "admin",
}

IDENTITY_TENANTS = {
    "customer_a": "tenant_a",
    "customer_b": "tenant_b",
    "administrator": "tenant_a",
}

IDENTITY_OWNERSHIP = {
    "customer_a": ["order_1001"],
    "customer_b": ["order_1002"],
    "administrator": [],
}


def get_role(identity: str) -> str | None:
    return ROLES.get(identity)


def get_identities() -> list[dict]:
    return [dict(v) for v in IDENTITIES.values()]


def role_map() -> dict[str, str]:
    return dict(ROLES)
