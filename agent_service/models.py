"""Input, output and tool-evidence models for the demo agent."""

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=5, max_length=1000)


class ToolExecution(BaseModel):
    tool_name: str
    request: dict[str, Any]
    http_status: int
    response: dict[str, Any]


class AgentRunResponse(BaseModel):
    model: str
    final_message: str
    tool_executions: list[ToolExecution]