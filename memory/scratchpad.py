from collections import deque

MAX_SCRATCHPAD_CHARS = 8000   # ~2000 tokens, leaves room for prompt + output

class Scratchpad:
    def __init__(self, max_entries: int = 20):
        self._entries: deque[str] = deque(maxlen=max_entries)

    def add_observation(self, text: str):
        self._entries.append(f"[Observation] {text}")

    def add_action(self, tool: str, args: dict, result: str):
        self._entries.append(
            f"[Action] Tool={tool} Args={args}\n[Result] {result}"
        )

    def format(self) -> str:
        return "\n".join(self._entries)
    

    def get_trimmed(self) -> str:
        """Return the scratchpad truncated to the most recent content."""
        full = self.get()   # your existing method
        if len(full) <= MAX_SCRATCHPAD_CHARS:
            return full
        # Keep the tail — most recent searches are most relevant
        trimmed = full[-MAX_SCRATCHPAD_CHARS:]
        # Don't cut mid-line
        first_newline = trimmed.find("\n")
        if first_newline > 0:
            trimmed = trimmed[first_newline + 1:]
        return "[...earlier research truncated...]\n" + trimmed