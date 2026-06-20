import json
import re
from langchain_ollama import OllamaLLM
from .state import AgentState, ToolCall


PLANNER_PROMPT = """You are a research agent planner. Given the task and scratchpad below, decide the next tool to call.

Available tools:
{tool_descriptions}

Current task: {task}

Scratchpad (what has happened so far):
{scratchpad}

Respond ONLY with valid JSON in this exact format:
{{
  "tool_name": "<tool name>",
  "args": {{ <args dict> }}
}}

Do not explain. Output JSON only."""


class Planner:
    def __init__(self, llm: OllamaLLM, tool_descriptions: str):
        self.llm = llm
        self.tool_descriptions = tool_descriptions

    def decide(self, state: AgentState) -> ToolCall:
        prompt = PLANNER_PROMPT.format(
            tool_descriptions=self.tool_descriptions,
            task=state.task,
            scratchpad=state.scratchpad or "(empty)",
        )
        response = self.llm.invoke(prompt)

        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?|```", "", response).strip()

        try:
            parsed = json.loads(clean)
            return ToolCall(tool_name=parsed["tool_name"], args=parsed["args"])
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Planner returned invalid JSON: {response}") from e