"""Analyse workflow transitions against the state model."""

from workflows.state_model import (
    INVALID_TRANSITIONS,
    VALID_TRANSITIONS,
    is_valid_transition,
)


def analyze_transition(from_state: str, to_state: str) -> dict:
    valid = is_valid_transition(from_state, to_state)
    return {
        "from_state": from_state,
        "to_state": to_state,
        "valid": valid,
        "expected_status": 200 if valid else 400,
    }


def analyze_all() -> list[dict]:
    results = []
    for from_state, to_state in sorted(VALID_TRANSITIONS | INVALID_TRANSITIONS):
        results.append(analyze_transition(from_state, to_state))
    return results
