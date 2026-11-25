"""Discovery agent: returns the 8 lab endpoints (deterministic)."""

from agents.base import AgentInput, AgentOutput, BaseAgent
from database.store import STORE
from discovery.crawler import Crawler


class DiscoveryAgent(BaseAgent):
    name = "discovery"

    async def run(self, task: AgentInput) -> AgentOutput:
        scan = STORE.get_scan(task.scan_id) or {}
        lab = STORE.get_lab(task.lab_id) or {}
        crawler = Crawler(base_url=lab.get("base_url", "http://127.0.0.1:8000"))
        endpoints = crawler.crawl()
        STORE.update_scan(task.scan_id, {"endpoints_discovered": len(endpoints)})
        return AgentOutput(
            status="complete",
            observations=[{"type": "endpoint", **e} for e in endpoints],
            confidence=1.0,
        )
