import json
import re
from langchain_groq import ChatGroq
from .state import AgentState, ToolCall
from agent.prompts.planner_prompt import PLANNER_PROMPT

MAX_SCRATCHPAD_CHARS = 6000
MAX_TASK_CHARS = 1500


def _to_text(response) -> str:
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, list):
            return "".join(
                str(part.get("text", part))
                for part in content
                if isinstance(part, dict)
            )
        return str(content)
    return str(response)


def _trim_scratchpad(scratchpad: str | None) -> str:
    if not scratchpad:
        return "(empty)"
    if len(scratchpad) <= MAX_SCRATCHPAD_CHARS:
        return scratchpad
    trimmed = scratchpad[-MAX_SCRATCHPAD_CHARS:]
    first_newline = trimmed.find("\n")
    if first_newline > 0:
        trimmed = trimmed[first_newline + 1:]
    return "[...earlier research truncated...]\n" + trimmed


def _trim_task(task: str) -> str:
    """
    The full task includes a long 6-step research template.
    For the planner we only need enough context to pick the next tool —
    truncate after MAX_TASK_CHARS so we don't burn tokens re-sending
    the entire prompt on every iteration.
    """
    if len(task) <= MAX_TASK_CHARS:
        return task
    return task[:MAX_TASK_CHARS] + "\n[...task truncated — follow steps in order...]"


class Planner:
    def __init__(self, llm: ChatGroq, tool_descriptions: str):
        self.llm = llm
        self.tool_descriptions = tool_descriptions

    def decide(self, state: AgentState) -> ToolCall:
        prompt = PLANNER_PROMPT.format(
            tool_descriptions=self.tool_descriptions,
            task=_trim_task(state.task),
            scratchpad=_trim_scratchpad(state.scratchpad),
        )
        response = self.llm.invoke(prompt)
        text = _to_text(response)

        clean = re.sub(r"```(?:json)?|```", "", text).strip()

        try:
            parsed = json.loads(clean)
            return ToolCall(tool_name=parsed["tool_name"], args=parsed["args"])
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Planner returned invalid JSON: {text!r}") from e