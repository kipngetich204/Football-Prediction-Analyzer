from collections import deque


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