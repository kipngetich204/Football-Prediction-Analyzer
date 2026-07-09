# How the LLM Is Leveraged Across This Codebase

This project uses a large language model as the reasoning core of an autonomous football-prediction pipeline. It is not just a one-off text generator; it is woven through the full research-and-prediction workflow from planning to final JSON output.

The active implementation uses an Ollama-hosted model via LangChain, with the default model set to qwen2.5:7b. The LLM is invoked through the same shared instance across the planner, reflector, synthesizer, and final structuring stage.

---

## 1. Where the LLM lives

The LLM is initialized in the main agent class in [agent/football_prediction_agent.py](agent/football_prediction_agent.py). That file creates a single OllamaLLM object and passes it into three specialist components:

- [agent/planner.py](agent/planner.py) — decides which tool to call next
- [agent/reflector.py](agent/reflector.py) — decides whether the research is sufficient
- [agent/synthesizer.py](agent/synthesizer.py) — writes the final narrative analysis

There is also a second, older research agent in [agent/core.py](agent/core.py) that uses the same pattern, but the main runtime path is the football prediction agent in [agent/football_prediction_agent.py](agent/football_prediction_agent.py).

---

## 2. What the LLM is responsible for

The LLM is the brain of the pipeline, while the tools do the data gathering. In this codebase, the LLM is used to:

1. Interpret the match task and decide the next research action
2. Evaluate whether the scratchpad contains enough evidence to produce a prediction
3. Turn raw research notes into a polished football analysis
4. Convert that analysis into a strict, nested JSON structure that the app can save and reuse

In other words, the LLM is doing decision-making, judgment, summarization, and formatting — not just writing prose.

---

## 3. The full LLM workflow for one match

When the app processes a single match, the LLM is called in a multi-step loop:

### Step A — Planning
The planner sends a prompt to the LLM asking it to choose the next tool call. The prompt is built from:

- the match task
- the current scratchpad
- a list of available tools

This happens once per iteration of the agent loop.

### Step B — Reflection
After a tool result is returned, the reflector asks the LLM whether the research is complete. It returns one of three values:

- done
- continue
- error

This also happens once per iteration.

### Step C — Synthesis
Once the loop exits, the synthesizer sends the accumulated research to the LLM and asks it to write a comprehensive football analysis.

### Step D — JSON structuring
Finally, the agent sends the synthesized analysis to the LLM again and asks it to return a precise JSON object matching the project schema.

That means the LLM is used for four distinct roles in the main flow:

- planner
- reflector
- synthesizer
- JSON formatter

---

## 4. How many times the LLM is called per match

The exact number depends on how many iterations the agent needs before it decides the research is sufficient.

### Current implementation logic

For each match, the code performs:

- 1 planner call per loop iteration
- 1 reflector call per loop iteration
- 1 synthesizer call once the loop finishes
- 1 final JSON-structuring call

If the agent completes in $k$ iterations, the total number of LLM calls is:

$$
2k + 2
$$

A concrete example is visible in [trajectories/prediction_1782212026.json](trajectories/prediction_1782212026.json), where the run stopped after three tool calls and therefore used only the early planner/reflector stages before exiting.

### Practical ranges

- Minimum per match: 4 calls
  - 1 planner
  - 1 reflector
  - 1 synthesizer
  - 1 JSON structuring call

- Typical per match: roughly 4 to 8 calls
  - the agent often finishes once enough evidence is collected

- Maximum per match with the current setting: 22 calls
  - because the main agent allows up to 10 iterations
  - $2 \times 10 + 2 = 22$

### Important detail
The loop contains safeguards to stop repeated research. If the same tool query is attempted too many times, the agent forces an exit. That prevents runaway LLM usage.

---

## 5. How many times it is called for a full daily run

The batching logic in [agent/football_prediction_agent.py](agent/football_prediction_agent.py) processes each match in the payload one by one.

If a daily file contains $N$ non-finished matches and each one uses $k$ iterations, then the total LLM calls are approximately:

$$
N \times (2k + 2)
$$

Examples:

- 10 matches, each finishing in 1 iteration: about 40 LLM calls
- 10 matches, each finishing in 5 iterations: about 120 LLM calls
- 20 matches, each reaching the maximum loop length: about 440 LLM calls

### Important constraint in the current code
The batch runner skips matches whose status is Finished. So the LLM is only used for non-finished matches.

---

## 6. The prompt templates that drive the LLM

The project uses four prompt templates, each with a different purpose:

- [agent/prompts/planner_prompt.py](agent/prompts/planner_prompt.py)
  - instructs the LLM to choose the next tool call
  - enforces a strict JSON output format
  - prevents repeated searches

- [agent/prompts/reflection_prompt.py](agent/prompts/reflection_prompt.py)
  - asks the LLM to judge whether the research is sufficient
  - returns a short verdict: done, continue, or error

- [agent/prompts/synthesis_prompt.py](agent/prompts/synthesis_prompt.py)
  - asks the LLM to write a detailed football analysis from the gathered evidence
  - tells it to be explicit about missing information rather than inventing facts

- [agent/prompts/json_structure_prompt.py](agent/prompts/json_structure_prompt.py)
  - forces the LLM to return a structured JSON object
  - defines the schema for confidence, value rating, predictions, injury alerts, expected goals, and more

These prompts are a major part of the system design: they turn the LLM into a constrained, schema-aware prediction engine.

---

## 7. What the LLM output becomes

The LLM-generated analysis is not left as raw text. It is converted into a structured prediction object with fields such as:

- expected score
- confidence score
- risk level
- value rating
- win probabilities
- expected goals
- form summary
- head-to-head summary
- injury alert
- tiered predictions for basic, premium, and super premium
- alternative tip

This structured output is assembled in [agent/football_prediction_agent.py](agent/football_prediction_agent.py) and saved as a prediction JSON file by the CLI runners in [app/main.py](app/main.py) and [app/football_main.py](app/football_main.py).

---

## 8. How the LLM is used in the entry points

The CLI entry points instantiate the agent and hand the full payload to it:

- [app/main.py](app/main.py) — lightweight runner
- [app/football_main.py](app/football_main.py) — fuller runner with Firebase persistence and snapshot logic

Both entry points create a FootballPredictionAgent and call predict_all_matches, which in turn calls predict_match for each qualifying match. That is the top-level trigger for the entire LLM-driven process.

---

## 9. What is not handled by the LLM

The codebase deliberately separates research and reasoning:

- web search is performed by tool-based components
- arithmetic and simple statistical calculations are handled separately
- the LLM is used to interpret, synthesize, and structure the results

So the LLM is not doing the web lookup itself; it is consuming the search output and turning it into a prediction.

---

## 10. Reliability and fallback behavior

The implementation includes several safeguards around LLM output:

- If the planner returns malformed JSON, the agent raises an error and stops that branch
- If the reflector returns an invalid verdict, it defaults to continue
- If the same query repeats too many times, the loop is force-stopped
- If the final JSON parsing fails, the agent falls back to a default structured schema rather than crashing

This makes the system more robust, but it also means the LLM is a critical dependency whose output quality directly shapes the final prediction.

---

## 11. Bottom line

The LLM is the central intelligence layer of this project. It is used repeatedly for each match, not merely once at the end. In practice, the code is designed so that each match can trigger a small reasoning loop involving the planner, reflector, synthesizer, and final JSON formatter.

For a single match, the architecture supports:

- a minimum of 4 LLM calls
- a maximum of 22 LLM calls under the current settings
- a typical range of about 4 to 8 calls when the loop exits early

For a full daily batch, the total amount of LLM work scales linearly with the number of non-finished matches.
