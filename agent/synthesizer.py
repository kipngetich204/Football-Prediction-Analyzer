from langchain_groq import ChatGroq
from .state import AgentState
from agent.prompts.synthesis_prompt import SYNTHESIS_PROMPT

# Synthesizer gets the most context — it needs to write the full analysis.
# But the task template itself is redundant here; a short match header is enough.
MAX_SCRATCHPAD_CHARS = 10000
MAX_TASK_CHARS = 300


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
        return "(no research collected)"
    if len(scratchpad) <= MAX_SCRATCHPAD_CHARS:
        return scratchpad
    trimmed = scratchpad[-MAX_SCRATCHPAD_CHARS:]
    first_newline = trimmed.find("\n")
    if first_newline > 0:
        trimmed = trimmed[first_newline + 1:]
    return "[...earlier research truncated — use what follows...]\n" + trimmed


def _match_header(task: str) -> str:
    """
    Extract just the match identity from the full research task.
    The synthesizer doesn't need the 6-step instructions — it needs
    to know *what* match it is writing about.
    """
    lines = [line.strip() for line in task.splitlines() if line.strip()]
    kept = []
    for line in lines:
        kept.append(line)
        if len("\n".join(kept)) >= MAX_TASK_CHARS:
            break
    return "\n".join(kept)


class Synthesizer:
    def __init__(self, llm: ChatGroq):
        self.llm = llm

    def compile(self, state: AgentState) -> str:
        prompt = SYNTHESIS_PROMPT.format(
            task=_match_header(state.task),
            scratchpad=_trim_scratchpad(state.scratchpad),
        )
        return _to_text(self.llm.invoke(prompt))