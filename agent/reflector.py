from langchain_groq import ChatGroq
from .state import AgentState
from agent.prompts.reflection_prompt import REFLECTION_PROMPT

MAX_SCRATCHPAD_CHARS = 4000  # reflector needs less context than planner
MAX_TOOL_RESULT_CHARS = 2000  # last result only needs a snapshot
MAX_TASK_CHARS = 400          # reflector only needs to know the match, not all 6 steps


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


def _trim(text: str | None, max_chars: int, label: str = "") -> str:
    if not text:
        return "(empty)"
    if len(text) <= max_chars:
        return text
    trimmed = text[-max_chars:]
    first_newline = trimmed.find("\n")
    if first_newline > 0:
        trimmed = trimmed[first_newline + 1:]
    prefix = f"[...{label} truncated...]\n" if label else "[...truncated...]\n"
    return prefix + trimmed


def _short_task(task: str) -> str:
    """
    Strip the full research template down to just the match identity line.
    The reflector only needs to know what match is being analyzed and
    how many steps exist — not the full prompt text.
    """
    lines = [line.strip() for line in task.splitlines() if line.strip()]
    # Keep lines up to and including the first STEP reference so the
    # reflector knows the structure, then stop.
    kept = []
    for line in lines:
        kept.append(line)
        if len("\n".join(kept)) >= MAX_TASK_CHARS:
            break
    return "\n".join(kept) + "\n[...full task truncated — evaluate research completeness only...]"


class Reflector:
    def __init__(self, llm: ChatGroq):
        self.llm = llm

    def evaluate(self, state: AgentState, tool_result: str) -> str:
        prompt = REFLECTION_PROMPT.format(
            task=_short_task(state.task),
            scratchpad=_trim(state.scratchpad, MAX_SCRATCHPAD_CHARS, "earlier research"),
            tool_result=_trim(tool_result, MAX_TOOL_RESULT_CHARS, "tool result"),
        )
        response = self.llm.invoke(prompt)
        text = _to_text(response).strip().lower()

        # Extract just the verdict word — model sometimes adds punctuation or a sentence
        for verdict in ("done", "continue", "error"):
            if verdict in text:
                return verdict

        return "continue"