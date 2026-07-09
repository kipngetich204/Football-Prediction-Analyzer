import time
import json
import logging
from pathlib import Path
from langchain_groq import ChatGroq

from .state import AgentState, AgentStatus, ToolResult
from .planner import Planner
from .reflector import Reflector
from .synthesizer import Synthesizer
from tools.registry import ToolRegistry
from tools.web_search import WebSearchTool
from tools.calculator import CalculatorTool
from memory.scratchpad import Scratchpad

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8
TRAJECTORY_DIR = Path("trajectories")


class ResearchAgent:
    def __init__(
        self,
        groq_api_key: str,
        model: str = "llama-3.1-8b-instant",
    ):
        self.llm = ChatGroq(
            model=model,
            api_key=groq_api_key,
            temperature=0.1,
            max_tokens=2048,
        )
        # Register the tools available to the agent.
        self.registry = ToolRegistry()
        self.registry.register(WebSearchTool())
        self.registry.register(CalculatorTool())

        self.planner = Planner(self.llm, self.registry.list_all())
        self.reflector = Reflector(self.llm)
        self.synthesizer = Synthesizer(self.llm)

        TRAJECTORY_DIR.mkdir(exist_ok=True)

    def run(self, task: str) -> str:
        state = AgentState(task=task)
        scratchpad = Scratchpad()
        trajectory = []

        logger.info(f"Starting agent for task: {task}")

        while state.iteration_count < MAX_ITERATIONS:
            state.iteration_count += 1
            logger.info(f"Iteration {state.iteration_count}")

            # Ask the planner which tool should be used next.
            try:
                tool_call = self.planner.decide(state)
            except ValueError as e:
                logger.error(f"Planner failed: {e}")
                state.status = AgentStatus.ERROR
                break

            logger.info(f"Planned tool: {tool_call.tool_name} with args: {tool_call.args}")

            # Run the chosen tool and record the result.
            tool = self.registry.get(tool_call.tool_name)
            if tool is None:
                output = f"Unknown tool: {tool_call.tool_name}"
                success = False
            else:
                output, success = tool.safe_run(tool_call.args)

            result = ToolResult(
                tool_name=tool_call.tool_name,
                args=tool_call.args,
                output=output,
                success=success,
            )
            state.add_tool_result(result)
            scratchpad.add_action(tool_call.tool_name, tool_call.args, output)

            trajectory.append({
                "iteration": state.iteration_count,
                "tool": tool_call.tool_name,
                "args": tool_call.args,
                "output": output,
                "success": success,
            })

            # Decide whether the current research is sufficient.
            decision = self.reflector.evaluate(state, output)
            logger.info(f"Reflector decision: {decision}")

            if decision == "done":
                state.status = AgentStatus.DONE
                break
            elif decision == "error" and not success:
                # Exponential backoff before retry
                time.sleep(2 ** (state.iteration_count - 1))

        else:
            state.status = AgentStatus.MAX_ITER

        # Create the final written analysis from the collected evidence.
        final_answer = self.synthesizer.compile(state)
        state.final_answer = final_answer

        # Save the agent's step-by-step path for later inspection.
        self._save_trajectory(task, trajectory, final_answer)

        return final_answer

    def _save_trajectory(self, task: str, trajectory: list, answer: str):
        import time as t
        filename = TRAJECTORY_DIR / f"trajectory_{int(t.time())}.json"
        with open(filename, "w") as f:
            json.dump({"task": task, "trajectory": trajectory, "answer": answer}, f, indent=2)
        logger.info(f"Trajectory saved to {filename}")