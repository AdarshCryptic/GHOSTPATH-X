"""Order workflow state model: created -> paid -> shipped."""

STATES = ["created", "paid", "shipped"]

VALID_TRANSITIONS = {
    ("created", "paid"),
    ("paid", "shipped"),
}

INVALID_TRANSITIONS = {
    ("shipped", "created"),
    ("paid", "created"),
    ("created", "shipped"),
}


def is_valid_transition(from_state: str, to_state: str) -> bool:
    return (from_state, to_state) in VALID_TRANSITIONS


def get_states() -> list[str]:
    return list(STATES)


def get_valid_transitions() -> list[tuple[str, str]]:
    return sorted(VALID_TRANSITIONS)


def get_invalid_transitions() -> list[tuple[str, str]]:
    return sorted(INVALID_TRANSITIONS)
