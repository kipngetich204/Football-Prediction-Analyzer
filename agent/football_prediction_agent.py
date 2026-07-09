"""
Football Prediction Agent — Structured Nested Dict Output
Researches matches via web search and returns fully structured Tiptype-compatible predictions.
"""

from collections import Counter
import json
import os
import re
import time
import logging
from pathlib import Path
from langchain_groq import ChatGroq


def _to_text(response) -> str:
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, list):
            return "".join(str(part.get("text", part)) for part in content if isinstance(part, dict))
        return str(content)
    return str(response)

from agent.state import AgentState, AgentStatus, ToolResult
from agent.planner import Planner
from agent.reflector import Reflector
from agent.synthesizer import Synthesizer
from tools.registry import ToolRegistry
from tools.web_search import WebSearchTool
from tools.calculator import CalculatorTool
from memory.scratchpad import Scratchpad
from agent.prompts.json_structure_prompt import JSON_STRUCTURE_PROMPT
from agent.prompts.research_task_template import RESEARCH_TASK_TEMPLATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
TRAJECTORY_DIR = Path("trajectories")

# Resolve the outcome of completed matches once the final score is known.

def resolve_match_status( structured: dict, score: str) -> dict:
    """
    For a finished match, walk every prediction in every tier
    and set its result to 'won' or 'lost'.
    """
    try:
        parts = score.replace(" ", "").split("-")
        home_goals, away_goals = int(parts[0]), int(parts[1])
    except Exception:
        return structured

    def _resolve(market: str, prediction: str) -> str:
        total = home_goals + away_goals
        m = market.strip()
        p = prediction.strip()

        if m in ("Over 1.5", "Over 2.5", "Over 3.5"):
            threshold = float(m.split()[1])
            return "won" if total > threshold else "lost"

        if m == "GG":
            both = home_goals >= 1 and away_goals >= 1
            return "won" if (p == "Yes" and both) or (p == "No" and not both) else "lost"

        if m == "Match Result":
            if p == "1": return "won" if home_goals > away_goals else "lost"
            if p == "X": return "won" if home_goals == away_goals else "lost"
            if p == "2": return "won" if away_goals > home_goals else "lost"

        if m == "Double Chance":
            home_win = home_goals > away_goals
            draw     = home_goals == away_goals
            away_win = away_goals > home_goals
            if p == "1X": return "won" if home_win or draw else "lost"
            if p == "12": return "won" if home_win or away_win else "lost"
            if p == "X2": return "won" if draw or away_win else "lost"

        if m == "Draw No Bet":
            if home_goals == away_goals: return "pending"  # void/refund
            if p == "Home": return "won" if home_goals > away_goals else "lost"
            if p == "Away": return "won" if away_goals > home_goals else "lost"

        if m == "Correct Score":
            return "won" if p == f"{home_goals}-{away_goals}" else "lost"

        if m.startswith("HT/FT"):
            # Requires HT score — can't resolve without it
            return "pending"

        if m == "Winning Margin":
            diff = home_goals - away_goals
            if p == "Home by 1": return "won" if diff == 1 else "lost"
            if p == "Home by 2": return "won" if diff == 2 else "lost"
            if p == "Away by 1": return "won" if diff == -1 else "lost"
            if p == "Away by 2": return "won" if diff == -2 else "lost"

        if m == "First Team To Score":
            # Can't resolve without minute-by-minute data
            return "pending"

        return "pending"

    for tier in ("basic", "premium", "super_premium"):
        tier_block = structured.get("predictions", {}).get(tier, {})
        for pred in tier_block.get("predictions", []):
            pred["result"] = _resolve(pred.get("market", ""), pred.get("prediction", ""))

    return structured



class FootballPredictionAgent:
    """
    Autonomous agent that generates structured football predictions
    by conducting multi-step web research and returning fully nested dicts.
    """

    def __init__(self, groq_api_key: str | None = None ):
        resolved_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not resolved_key:
            raise ValueError("A Groq API key is required. Set GROQ_API_KEY in your environment or pass groq_api_key explicitly.")

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=resolved_key,
            temperature=0.1,
            max_tokens=1024,
        )

        self.registry = ToolRegistry()
        self.registry.register(WebSearchTool())
        self.registry.register(CalculatorTool())

        self.planner = Planner(self.llm, self.registry.list_all())
        self.reflector = Reflector(self.llm)
        self.synthesizer = Synthesizer(self.llm)
 

        TRAJECTORY_DIR.mkdir(exist_ok=True)

    # Handle one match from the daily payload.

    def predict_match(self, match_data: dict) -> dict:
        """
        Research and predict a single match.

        Args:
            match_data: One match object from the daily payload

        Returns:
            Fully structured prediction dict (Tiptype-compatible + new fields)
        """
        home_team    = match_data.get("homeTeam", "Unknown")
        away_team    = match_data.get("awayTeam", "Unknown")
        league       = match_data.get("league", "Unknown")
        date         = match_data.get("date", "Unknown")
        market       = match_data.get("markets", "Over 2.5 Goals")
        match_status = match_data.get("matchStatus", "Not Started")
        score        = match_data.get("score", "0-0")
        date_year    = date[:4] if date else "2026"

        # Provide a market-specific keyword for later research steps.
        market_keywords = {
            "Over 2.5 Goals": "over 2.5 goals percentage",
            "GG":             "both teams to score percentage",
            "1X2":            "win probability percentage",
            "Handicap":       "winning margin goals",
            "BTTS":           "both teams scored percentage",
        }
        market_keyword = market_keywords.get(market, "goals statistics")

        status_instruction = (
            f"  - Resolve status to 'won' or 'lost' — actual score was {score}"
            if match_status == "Finished"
            else "  - Status remains 'pending' (match not yet played)"
        )

        task = RESEARCH_TASK_TEMPLATE.format(
            home_team=home_team,
            away_team=away_team,
            league=league,
            date=date,
            date_year=date_year,
            #market=market,
            #market_keyword=market_keyword,
            match_status=match_status,
            #score=score,
            status_instruction=status_instruction,
        )
        logger.info(f"Task:\n{task}")
        # Run the planning and reflection loop until the research is sufficient.
        state       = AgentState(task=task)
        scratchpad  = Scratchpad()
        trajectory  = []

        logger.info(f"Predicting: {home_team} vs {away_team} ({league})")

        query_counter: Counter = Counter()
        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1
            state.iteration_count = iteration
            logger.info(f"  Iteration {iteration}/{MAX_ITERATIONS}")

            try:
                tool_call = self.planner.decide(state)
            except ValueError as e:
                logger.error(f"  Planner error: {e}")
                state.status = AgentStatus.ERROR
                break

            # Stop the loop if the same action is being repeated too often.
            call_key = f"{tool_call.tool_name}::{json.dumps(tool_call.args, sort_keys=True)}"
            query_counter[call_key] += 1
            if query_counter[call_key] >= 3:
                logger.warning(f"  Loop detected on '{call_key}' — forcing finish")
                state.status = AgentStatus.DONE
                break

            logger.info(f"  → {tool_call.tool_name}({tool_call.args})")

            tool = self.registry.get(tool_call.tool_name)
            if tool is None:
                output, success = f"Unknown tool: {tool_call.tool_name}", False
            else:
                output, success = tool.safe_run(tool_call.args)

            state.add_tool_result(ToolResult(
                tool_name=tool_call.tool_name,
                args=tool_call.args,
                output=output,
                success=success,
            ))
            scratchpad.add_action(tool_call.tool_name, tool_call.args, output)

            trajectory.append({
                "iteration": iteration,
                "tool": tool_call.tool_name,
                "args": tool_call.args,
                "success": success,
            })

            decision = self.reflector.evaluate(state, output)
            logger.info(f"  Reflector: {decision}")

            if decision == "done":
                state.status = AgentStatus.DONE
                break
            elif decision == "error" and not success:
                time.sleep(2 ** (iteration - 1))
        else:
            state.status = AgentStatus.MAX_ITER

        # Turn the collected research into a narrative analysis.
        raw_analysis = self.synthesizer.compile(state)
        state.final_answer = raw_analysis

        # Convert the analysis into the structured prediction schema.
        structured = self._structure_prediction(raw_analysis, match_data)

        # Fill in the result field for completed matches using the actual score.

        if match_status == "Finished":
            structured = resolve_match_status(structured, score)

        self._save_trajectory(task, trajectory, structured)
        return structured

    # Process the full list of matches for a day.

    def predict_all_matches(self, payload: dict) -> dict:
        """
        Process a full daily matches payload.

        Args:
            payload: Full JSON payload containing 'matches' array

        Returns:
            Complete structured output with all predictions and summary
        """
        matches   = payload.get("matches", [])
        date      = payload.get("date", "")
        total     = len(matches)
        results   = []

        logger.info(f"Processing {total} matches for {date}")

        for idx, match in enumerate(matches, 1):
            if match.get("matchStatus")== "Finished":
                logger.info(f"skipping match: {match.get('id')}")
                continue
            logger.info(f"\n[{idx}/{total}] {match.get('homeTeam')} vs {match.get('awayTeam')}")
            result = self.predict_match(match)
            results.append(result)
            if idx < total:
                time.sleep(3)   # 3 second pause between matches — reduces 429s

        # Assign tip_of_the_day to the single highest-confidence match
        if results:
            best_idx = max(
                range(len(results)),
                key=lambda i: results[i].get("confidence_score", 0),
            )
            for i, m in enumerate(results):
                m["tip_of_the_day"] = (i == best_idx)

            tip_label = (
                f"{results[best_idx]['homeTeam']} vs {results[best_idx]['awayTeam']}"
            )
        else:
            tip_label = None

        # Build summary
        summary = {
            "basic":         sum(
                1 for m in results
                if m.get("predictions", {}).get("basic", {}).get("predictions")
            ),
            "premium":       sum(
                1 for m in results
                if m.get("predictions", {}).get("premium", {}).get("predictions")
            ),
            "super_premium": sum(
                1 for m in results
                if m.get("predictions", {}).get("super_premium", {}).get("predictions")
            ),
            "tip_of_the_day": tip_label,
        }

        return {
            "date":         date,
            "generated_at": payload.get("fetched_at", ""),
            "total":        total,
            "summary":      summary,
            "matches":      results,
        }

    # Turn the research summary into a structured prediction object.

    def _structure_prediction(self, raw_analysis: str, match_data: dict) -> dict:
        """
        Ask the LLM to convert free-text analysis into the structured JSON schema,
        then merge with the preserved original match fields.
        """
        home_team    = match_data.get("homeTeam", "Unknown")
        away_team    = match_data.get("awayTeam", "Unknown")
        league       = match_data.get("league", "Unknown")
        #market       = match_data.get("markets", "Over 2.5 Goals")
        match_status = match_data.get("matchStatus", "Not Started")
        score        = match_data.get("score", "0-0")

        prompt = JSON_STRUCTURE_PROMPT.format(
            home_team=home_team,
            away_team=away_team,
            league=league,
            score=score,
            match_status=match_status,
            raw_analysis=raw_analysis,
        )

        logger.info("  Structuring analysis into JSON...")
        raw_json = _to_text(self.llm.invoke(prompt))
        parsed   = self._parse_json(raw_json)

        # Merge: preserved input fields take priority for identity fields;
        # LLM output fills all prediction fields.
        return {
            # ── Preserved from input ──────────────────────────────────
            "id":          match_data.get("id", ""),
            "livescoreId": match_data.get("livescoreId", ""),
            "date":        match_data.get("date", ""),
            "league":      league,
            "homeTeam":    home_team,
            "awayTeam":    away_team,
            "time":        match_data.get("time", ""),
            "score":       score,
            "matchStatus": match_status,
            #"markets":     market,
            # ── From LLM structured output ────────────────────────────
            **parsed,
        }

    def _parse_json(self, raw: str) -> dict:
        """
        Robustly extract a JSON object from LLM output.
        Strips markdown fences, finds the outermost { }, falls back to defaults.
        """
        # Remove any markdown fences before trying to parse the JSON.
        clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        # Extract the first JSON object from the response body.
        brace_match = re.search(r"\{[\s\S]*\}", clean)
        if brace_match:
            clean = brace_match.group(0)

        # Parse the cleaned text into a Python dictionary.
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.warning(f"  JSON parse failed ({e}) — using safe defaults")
            return self._default_fields()


    @staticmethod
    def _default_fields() -> dict:
        """Safe fallback when the LLM fails to return valid JSON."""

        def _empty_tier(confidence_floor: int) -> dict:
            return {
                "reason": "Research data unavailable.",
                "predictions": [
                    {
                        "market":     "Over 1.5",
                        "prediction": "",
                        "confidence": confidence_floor,
                        "result":     None,
                    }
                ],
            }

        return {
            "reason":           "Insufficient data returned from research.",
            "expected_score":   "N/A",
            "confidence_score": 0,
            "risk_level":       "High",
            "value_rating":     1,
            "status":           "pending",
            "tip_of_the_day":   False,
            "match_importance": "Medium",
            "league_round":     "Unknown",
            "referee":          None,
            "win_probabilities": {"home": 34, "draw": 33, "away": 33},
            "expected_goals":    {"home": 1.0, "away": 1.0},
            "form":              {"home": "UNKNOWN", "away": "UNKNOWN"},
            "h2h_summary": {
                "played":       0,
                "home_wins":    0,
                "draws":        0,
                "away_wins":    0,
                "avg_goals":    0.0,
                "last_meeting": "No data available",
            },
            "key_factors":  ["Research data unavailable."],
            "injury_alert": {
                "active":    False,
                "home_team": "No data",
                "away_team": "No data",
            },
            "predictions": {
                "basic":         _empty_tier(80),
                "premium":       _empty_tier(65),
                "super_premium": _empty_tier(45),
            },
            "alternative_tip": {
                "market":     "N/A",
                "prediction": "N/A",
                "reason":     "No data available.",
                "confidence": 0,
            },
        }



        # ------------------------------------------------------------------
        # Private: persistence
        # ------------------------------------------------------------------

    def _save_trajectory(self, task: str, trajectory: list, answer: dict):
        """Save research trajectory and final structured output to JSON."""
        import time as t
        filename = TRAJECTORY_DIR / f"prediction_{int(t.time())}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"task": task, "trajectory": trajectory, "answer": answer}, f, indent=2)
        logger.info(f"  Trajectory → {filename}")
