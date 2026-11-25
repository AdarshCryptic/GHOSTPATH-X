"""Identity tests — identity/role_registry.py + lab/target.py IDENTITIES.

Contract: 3 identities; roles customer / customer / admin; ownership
mapping customer_a -> order_1001, customer_b -> order_1002.
"""

from identity.role_registry import (
    IDENTITY_OWNERSHIP,
    IDENTITY_TENANTS,
    ROLES,
    get_identities,
    get_role,
    role_map,
)
from lab.target import IDENTITIES


def test_three_identities():
    identities = get_identities()
    assert len(identities) == 3
    assert {i["identity"] for i in identities} == {
        "customer_a",
        "customer_b",
        "administrator",
    }
    assert set(IDENTITIES) == {"customer_a", "customer_b", "administrator"}


def test_roles_customer_customer_admin():
    assert role_map() == {
        "customer_a": "customer",
        "customer_b": "customer",
        "administrator": "admin",
    }
    assert ROLES == role_map()
    assert get_role("customer_a") == "customer"
    assert get_role("customer_b") == "customer"
    assert get_role("administrator") == "admin"
    assert get_role("nobody") is None


def test_ownership_mapping():
    assert IDENTITY_OWNERSHIP["customer_a"] == ["order_1001"]
    assert IDENTITY_OWNERSHIP["customer_b"] == ["order_1002"]
    assert IDENTITY_OWNERSHIP["administrator"] == []
    # Cross-check against the lab target's own identity table.
    assert IDENTITIES["customer_a"]["owns"] == ["order_1001"]
    assert IDENTITIES["customer_b"]["owns"] == ["order_1002"]
    assert "order_1002" not in IDENTITIES["customer_a"]["owns"]
    assert "order_1001" not in IDENTITIES["customer_b"]["owns"]


def test_tenant_mapping():
    assert IDENTITY_TENANTS == {
        "customer_a": "tenant_a",
        "customer_b": "tenant_b",
        "administrator": "tenant_a",
    }
    assert IDENTITIES["customer_a"]["tenant"] == "tenant_a"
    assert IDENTITIES["customer_b"]["tenant"] == "tenant_b"
