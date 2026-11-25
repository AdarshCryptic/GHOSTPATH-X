"""Deterministic crawler: deduplicates endpoints by method + path template.

No network access — the crawler works from the known lab inventory.
"""

from discovery.api_inventory import get_inventory


def dedupe_endpoints(endpoints: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for endpoint in endpoints:
        key = (endpoint["method"].upper(), endpoint["path"])
        if key not in seen:
            seen.add(key)
            out.append(dict(endpoint))
    return out


class Crawler:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url

    def crawl(self) -> list[dict]:
        return dedupe_endpoints(get_inventory())
