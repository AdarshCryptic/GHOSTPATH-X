"""Agent base types."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    lab_id: str
    scan_id: str
    task_id: str = "task-1"


class AgentOutput(BaseModel):
    status: str = "complete"
    observations: list[dict] = Field(default_factory=list)
    confidence: float = 1.0
    errors: list[str] = Field(default_factory=list)


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, task: AgentInput) -> AgentOutput:
        raise NotImplementedError
