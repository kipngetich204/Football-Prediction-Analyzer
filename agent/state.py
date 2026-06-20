from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class AgentStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    MAX_ITER = "max_iterations_reached"


@dataclass
class ToolCall:
    tool_name: str
    args: dict


@dataclass
class ToolResult:
    tool_name: str
    args: dict
    output: str
    success: bool


@dataclass
class AgentState:
    task: str
    scratchpad: str = ""
    tool_history: list[ToolResult] = field(default_factory=list)
    final_answer: Optional[str] = None
    iteration_count: int = 0
    status: AgentStatus = AgentStatus.RUNNING

    def update_scratchpad(self, text: str):
        self.scratchpad += f"\n{text}"

    def add_tool_result(self, result: ToolResult):
        self.tool_history.append(result)
        self.update_scratchpad(
            f"[Tool: {result.tool_name}] Args: {result.args}\nOutput: {result.output}"
        )