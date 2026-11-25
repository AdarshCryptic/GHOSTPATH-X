"""Reset the simulated lab to its initial state."""

from lab import target


def reset_lab_state() -> dict:
    target.reset_orders()
    return {"reset": True, "orders": ["order_1001", "order_1002"]}
