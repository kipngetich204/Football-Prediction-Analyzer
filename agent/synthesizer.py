from langchain_ollama import OllamaLLM
from .state import AgentState


SYNTHESIS_PROMPT = """You are a research assistant. Based on the research trajectory below, write a clear, well-structured final answer to the original task.

Task: {task}

Research trajectory:
{scratchpad}

Write a comprehensive answer with citations where possible. Be concise but complete."""


class Synthesizer:
    def __init__(self, llm: OllamaLLM):
        self.llm = llm

    def compile(self, state: AgentState) -> str:
        prompt = SYNTHESIS_PROMPT.format(
            task=state.task,
            scratchpad=state.scratchpad,
        )
        return self.llm.invoke(prompt)