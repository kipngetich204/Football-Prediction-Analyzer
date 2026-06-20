import json
from .base import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_all(self) -> str:
        descriptions = []
        for tool in self._tools.values():
            schema = tool.args_schema.model_json_schema()
            descriptions.append(
                f"Tool: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Args schema: {json.dumps(schema, indent=2)}"
            )
        return "\n\n".join(descriptions)