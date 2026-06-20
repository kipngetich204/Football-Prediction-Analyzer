from langchain_ollama import OllamaLLM
from .state import AgentState


REFLECTION_PROMPT = """You are evaluating whether a research agent has completed its task.

Task: {task}

Scratchpad:
{scratchpad}

Last tool result:
{tool_result}

Has the agent gathered enough information to write a final answer?
Reply with exactly one word: "done", "continue", or "error".

- "done": enough information to answer the task
- "continue": more tool calls needed
- "error": something went wrong and should be retried

Your reply:"""


class Reflector:
    def __init__(self, llm: OllamaLLM):
        self.llm = llm

    def evaluate(self, state: AgentState, tool_result: str) -> str:
        prompt = REFLECTION_PROMPT.format(
            task=state.task,
            scratchpad=state.scratchpad,
            tool_result=tool_result,
        )
        response = self.llm.invoke(prompt).strip().lower()

        if response not in ("done", "continue", "error"):
            return "continue"  # safe default
        return response