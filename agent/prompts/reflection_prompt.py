
REFLECTION_PROMPT = """You are evaluating a research agent's progress.

Task:
{task}

Scratchpad (all completed steps):
{scratchpad}

Last tool result:
{tool_result}

Answer these two questions internally, then give your verdict:
  A. How many of the numbered research steps in the task have been attempted?
  B. Does the scratchpad contain enough data to write a prediction
     (form strings, H2H record, xG/goals stats, injury notes)?

VERDICT RULES:
- "done"     → all steps attempted AND scratchpad has substantive data for a prediction
- "continue" → steps remain OR data is too thin (e.g. only 1-2 steps done out of 6)
- "error"    → the last tool call failed AND the same query has already been tried twice

IMPORTANT: If the scratchpad already shows 3+ repeated identical searches, reply "done"
to break the loop — the synthesizer will work with whatever data is available.

Reply with exactly one word: done, continue, or error."""