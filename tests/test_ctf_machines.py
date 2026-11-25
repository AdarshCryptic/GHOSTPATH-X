"""CTF Machines tests — GHOSTPATH X v0.3 free VM / lab catalogue.

Contract under test (v0.3):
  - GET  /api/v1/ctf-machines                 -> list of machines
  - GET  /api/v1/ctf-machines?source=...&difficulty=...&type=...&q=...
  - GET  /api/v1/ctf-machines/{machine_id}    -> one machine, 404 unknown
  - GET  /api/v1/ctf-machines/sources         -> list of platforms
  - POST /api/v1/ctf-machines/{machine_id}/solved {"solved": bool}
         -> updated machine with ``solved`` field (in-memory state)

The catalogue is static curated data (``ctf_machines/machines.py``):
no live scraping, no external calls at runtime. The honest-cost rule
is enforced here: platforms that are only partly free (HackTheBox,
CyberSecLabs, TryHackMe, Root-Me) must never be labelled plain "Free".
"""

import pytest

# Platforms that are NOT 100% free: a plain "Free" label would be a lie.
PARTLY_FREE_SOURCES = {"HackTheBox", "CyberSecLabs", "TryHackMe", "Root-Me"}
HONEST_LABELS = {"Free tier", "Free + paid"}

REQUIRED_MACHINE_FIELDS = {
    "id",
    "name",
    "source",
    "type",
    "cost_label",
    "difficulty",
    "topics",
    "homepage_url",
}


def _unwrap_list(payload, *keys):
    """Accept a bare list, or a list nested under one of ``keys``."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            if isinstance(payload.get(key), list):
                return payload[key]
    pytest.fail(
        "expected a list (or an object with one of "
        f"{keys}), got: {str(payload)[:300]}"
    )


def _list_machines(client, **params):
    resp = client.get("/api/v1/ctf-machines", params=params)
    assert resp.status_code == 200, (
        f"GET /api/v1/ctf-machines {params} failed: "
        f"{resp.status_code} {resp.text[:300]}"
    )
    return _unwrap_list(resp.json(), "machines", "items", "data", "results")


def _list_sources(client):
    resp = client.get("/api/v1/ctf-machines/sources")
    assert resp.status_code == 200, (
        f"GET /api/v1/ctf-machines/sources failed: "
        f"{resp.status_code} {resp.text[:300]}"
    )
    return _unwrap_list(resp.json(), "sources", "platforms", "items", "data", "results")


def _first_machine_id(client):
    machines = _list_machines(client)
    assert machines, "machine list is empty"
    return machines[0]["id"]


def test_list_returns_at_least_twenty_machines(client):
    machines = _list_machines(client)
    assert len(machines) >= 20, (
        f"expected >= 20 machines, got {len(machines)}"
    )


def test_filter_by_source_vulnhub(client):
    machines = _list_machines(client, source="VulnHub")
    assert len(machines) >= 1, "expected at least 1 VulnHub machine"
    for machine in machines:
        assert machine["source"] == "VulnHub", (
            f"{machine['id']} has source {machine['source']!r}, expected 'VulnHub'"
        )


def test_filter_by_difficulty_beginner(client):
    machines = _list_machines(client, difficulty="Beginner")
    assert len(machines) >= 1, "expected at least 1 Beginner machine"
    for machine in machines:
        assert machine["difficulty"] == "Beginner", (
            f"{machine['id']} has difficulty {machine['difficulty']!r}, "
            "expected 'Beginner'"
        )


def test_filter_by_type_downloadable_vm(client):
    machines = _list_machines(client, type="downloadable VM")
    assert len(machines) >= 1, "expected at least 1 downloadable VM"
    for machine in machines:
        assert machine["type"] == "downloadable VM", (
            f"{machine['id']} has type {machine['type']!r}, "
            "expected 'downloadable VM'"
        )


def test_search_mr_robot(client):
    machines = _list_machines(client, q="mr-robot")
    assert len(machines) >= 1, "search q=mr-robot returned nothing"
    assert any(
        "robot" in (m.get("name", "") + m.get("id", "")).lower()
        for m in machines
    ), f"search q=mr-robot did not return the Mr-Robot machine: {machines}"


def test_every_machine_has_required_fields_and_valid_homepage(client):
    machines = _list_machines(client)
    assert machines, "machine list is empty"
    for machine in machines:
        assert REQUIRED_MACHINE_FIELDS <= set(machine), (
            f"{machine.get('id', '?')} missing fields: "
            f"{REQUIRED_MACHINE_FIELDS - set(machine)}"
        )
        assert isinstance(machine["topics"], list) and machine["topics"], (
            f"{machine['id']} must have a non-empty topics list"
        )
        url = machine["homepage_url"]
        assert isinstance(url, str) and url.startswith("https://"), (
            f"{machine['id']} homepage_url must start with https://, got {url!r}"
        )
        assert " " not in url, (
            f"{machine['id']} homepage_url contains a space: {url!r}"
        )


def test_get_one_machine_and_404(client):
    machine_id = _first_machine_id(client)
    resp = client.get(f"/api/v1/ctf-machines/{machine_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == machine_id
    resp = client.get("/api/v1/ctf-machines/does-not-exist")
    assert resp.status_code == 404


def test_sources_returns_at_least_ten_platforms(client):
    sources = _list_sources(client)
    assert len(sources) >= 10, (
        f"expected >= 10 platforms, got {len(sources)}"
    )
    names = set()
    for source in sources:
        assert {"name", "cost_label", "type", "homepage_url", "description"} <= set(source), (
            f"source {source.get('name', '?')} missing fields"
        )
        assert source["name"] and source["name"] not in names, (
            f"duplicate or empty source name: {source['name']!r}"
        )
        names.add(source["name"])
        url = source["homepage_url"]
        assert isinstance(url, str) and url.startswith("https://"), (
            f"source {source['name']} homepage_url must start with https://, "
            f"got {url!r}"
        )
        assert " " not in url, (
            f"source {source['name']} homepage_url contains a space: {url!r}"
        )


def test_solved_toggle_roundtrip(client):
    machine_id = _first_machine_id(client)
    # Start clean: explicitly mark unsolved first.
    resp = client.post(
        f"/api/v1/ctf-machines/{machine_id}/solved", json={"solved": False}
    )
    assert resp.status_code == 200
    assert resp.json()["solved"] is False

    resp = client.post(
        f"/api/v1/ctf-machines/{machine_id}/solved", json={"solved": True}
    )
    assert resp.status_code == 200
    assert resp.json()["solved"] is True
    assert resp.json()["id"] == machine_id

    resp = client.get(f"/api/v1/ctf-machines/{machine_id}")
    assert resp.status_code == 200
    assert resp.json()["solved"] is True, (
        f"{machine_id} should show solved=true after marking solved"
    )

    # Reversing it must stick too.
    resp = client.post(
        f"/api/v1/ctf-machines/{machine_id}/solved", json={"solved": False}
    )
    assert resp.status_code == 200
    assert resp.json()["solved"] is False
    resp = client.get(f"/api/v1/ctf-machines/{machine_id}")
    assert resp.json()["solved"] is False


def test_solved_unknown_machine_404(client):
    resp = client.post(
        "/api/v1/ctf-machines/does-not-exist/solved", json={"solved": True}
    )
    assert resp.status_code == 404


def test_partly_free_sources_never_labelled_plain_free(client):
    machines = _list_machines(client)
    for machine in machines:
        if machine["source"] in PARTLY_FREE_SOURCES:
            assert machine["cost_label"] != "Free", (
                f"{machine['id']} ({machine['source']}) claims cost_label "
                f"'Free' — partly-free platforms must say 'Free tier' or "
                "'Free + paid'"
            )
            assert machine["cost_label"] in HONEST_LABELS, (
                f"{machine['id']} ({machine['source']}) has cost_label "
                f"{machine['cost_label']!r}, expected one of {sorted(HONEST_LABELS)}"
            )


def test_vulnhub_setup_steps_mention_virtualbox_and_host_only(client):
    machines = _list_machines(client, source="VulnHub")
    assert machines, "expected at least 1 VulnHub machine"
    for machine in machines:
        steps = machine.get("setup_steps")
        assert steps, f"{machine['id']} (VulnHub) has no setup_steps"
        text = " ".join(steps) if isinstance(steps, list) else str(steps)
        assert "VirtualBox" in text, (
            f"{machine['id']} setup_steps must mention VirtualBox: {text[:200]!r}"
        )
        assert "Host-Only" in text, (
            f"{machine['id']} setup_steps must mention Host-Only networking: "
            f"{text[:200]!r}"
        )
