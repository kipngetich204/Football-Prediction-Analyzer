"""
Football Prediction Agent — Structured Nested Dict Output
Researches matches via web search and returns fully structured Tiptype-compatible predictions.
"""

import json
import re
import time
import logging
from pathlib import Path
from langchain_ollama import OllamaLLM

from agent.state import AgentState, AgentStatus, ToolResult
from agent.planner import Planner
from agent.reflector import Reflector
from agent.synthesizer import Synthesizer
from tools.registry import ToolRegistry
from tools.web_search import WebSearchTool
from tools.calculator import CalculatorTool
from memory.scratchpad import Scratchpad

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
TRAJECTORY_DIR = Path("trajectories")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

RESEARCH_TASK_TEMPLATE = """
You are an elite autonomous football prediction analyst powered by real-time web research.

Analyze this match: {home_team} vs {away_team}
League / Tournament : {league}
Date                : {date}
Primary Market      : {market}
Match Status        : {match_status}
Score               : {score}

Complete ALL six research steps below using web search tools before forming any prediction.

STEP 1 — Recent Form
  • Search: "{home_team} last 5 matches results "
  • Search: "{away_team} last 5 matches results "
  → Extract: W/D/L string, goals scored/conceded avg, home/away split

STEP 2 — Head-to-Head History
  • Search: "{home_team} vs {away_team} head to head history"
  → Extract: total played, wins/draws, avg goals per game, last meeting result

STEP 3 — Injuries & Suspensions
  • Search: "{home_team} injury news lineup {date}"
  • Search: "{away_team} suspension injury {date}"
  → Extract: named absent players, confirmed lineup hints

STEP 4 — League / Tournament Context
  • Search: "{league} standings table "
  • Search: "{home_team} vs {away_team} match preview {date}"
  → Extract: league position, match importance, stakes (title/relegation/knockout)

STEP 5 — Market-Specific Research
  For market "{market}":
  • Search: "{home_team} {market_keyword} statistics "
  • Search: "{away_team} {market_keyword} statistics "
  → Extract: relevant percentage data aligned to the market

STEP 6 — Correct Score Research
  • Search: "{home_team} vs {away_team} correct score prediction xg "
  → Extract: most likely scoreline from xG models or expert tipsters

After ALL steps are complete, provide a comprehensive analysis that includes:
  - Primary prediction for market "{market}"
  - Confidence percentage (0–100)
  - Expected correct score (e.g. "2-1")
  - Win probabilities: home %, draw %, away % (must sum to 100)
  - Expected goals: home xG, away xG
  - Both teams' form last 5 as W/D/L string (e.g. "WWDLW")
  - H2H: played, home wins, draws, away wins, avg goals, last meeting
  - 3–5 specific key factors with real numbers
  - Injury alert for both teams
  - THREE-TIER PREDICTIONS:
      basic_prediction    → safest market (e.g. Over 1.5, Double Chance)
      premium_prediction  → main assigned market with good confidence
      super_premium       → highest-ceiling market, or null if not justified at 85%+
  - Alternative tip: a secondary market, or null
  - Risk level: Low / Medium / High
  - Value rating: 1–5
  - Match importance: Low / Medium / High / Critical
  - League round context (e.g. "Group Stage – Matchday 2")
  - Referee if found, else null
{status_instruction}

Be specific. Use real numbers. Never fabricate statistics.
"""

JSON_STRUCTURE_PROMPT = """
You are a JSON formatting assistant. Convert the football prediction analysis below into a
valid JSON object that strictly follows the schema shown. Return ONLY raw JSON — no markdown,
no explanation, no code fences, no trailing text.

SCHEMA:
{{
  "prediction":             "string — value matching the market (e.g. Over 2.5 | 1 | X | 2 | GG | NG | Yes | No | Home -1)",
  "reason":                 "string — 3-5 data-backed sentences",
  "type":                   "basic | premium | super-premium",
  "status":                 "pending | won | lost",
  "expected_score":         "string — e.g. 2-1",
  "confidence_score":       "integer 0-100",
  "risk_level":             "Low | Medium | High",
  "value_rating":           "integer 1-5",
  "tip_of_the_day":         false,
  "match_importance":       "Low | Medium | High | Critical",
  "league_round":           "string",
  "referee":                "string or null",
  "win_probabilities": {{
    "home":  "integer (% of 100)",
    "draw":  "integer (% of 100)",
    "away":  "integer (% of 100 — home+draw+away must equal 100)"
  }},
  "expected_goals": {{
    "home": "float",
    "away": "float"
  }},
  "form": {{
    "home": "string — W/D/L last 5, most recent first e.g. WWDLW",
    "away": "string — W/D/L last 5, most recent first e.g. LWWDD"
  }},
  "h2h_summary": {{
    "played":        "integer",
    "home_wins":     "integer",
    "draws":         "integer",
    "away_wins":     "integer",
    "avg_goals":     "float",
    "last_meeting":  "string — e.g. Brazil 3-0 Haiti (Mar 2025)"
  }},
  "key_factors": ["string", "string", "string"],
  "injury_alert": {{
    "active":     "boolean",
    "home_team":  "string — named absences or No significant injuries",
    "away_team":  "string — named absences or No significant injuries"
  }},
  "basic_prediction": {{
    "market":     "string",
    "prediction": "string",
    "reason":     "string — 2-3 sentences",
    "confidence": "integer 0-100"
  }},
  "premium_prediction": {{
    "market":     "string",
    "prediction": "string",
    "reason":     "string — 2-3 sentences",
    "confidence": "integer 0-100"
  }},
  "super_premium_prediction": "same structure as basic_prediction, or null",
  "alternative_tip": {{
    "market":     "string",
    "prediction": "string",
    "reason":     "string — 1-2 sentences",
    "confidence": "integer 0-100"
  }}
}}

MATCH CONTEXT:
  Home Team    : {home_team}
  Away Team    : {away_team}
  League       : {league}
  Market       : {market}
  Score        : {score}
  Match Status : {match_status}

RAW ANALYSIS:
{raw_analysis}
"""


# ---------------------------------------------------------------------------
# Helper: resolve status for finished matches
# ---------------------------------------------------------------------------

def resolve_match_status(prediction: str, market: str, score: str) -> str:
    """
    Determine won/lost for a finished match by applying market logic to actual score.
    Returns 'won', 'lost', or 'pending' on parse failure.
    """
    try:
        parts = score.replace(" ", "").split("-")
        home_goals, away_goals = int(parts[0]), int(parts[1])
        total_goals = home_goals + away_goals

        market_key = market.strip()
        pred = prediction.strip()

        if market_key == "Over 2.5 Goals":
            return "won" if (pred == "Over 2.5" and total_goals >= 3) or \
                            (pred == "Under 2.5" and total_goals <= 2) else "lost"

        if market_key == "GG":
            both_scored = home_goals >= 1 and away_goals >= 1
            return "won" if (pred == "GG" and both_scored) or \
                            (pred == "NG" and not both_scored) else "lost"

        if market_key == "1X2":
            if pred == "1": return "won" if home_goals > away_goals else "lost"
            if pred == "X": return "won" if home_goals == away_goals else "lost"
            if pred == "2": return "won" if away_goals > home_goals else "lost"

        if market_key == "BTTS":
            both_scored = home_goals >= 1 and away_goals >= 1
            return "won" if (pred == "Yes" and both_scored) or \
                            (pred == "No" and not both_scored) else "lost"

        if market_key == "Handicap":
            # Generic handicap resolution: extract handicap value from prediction string
            # e.g. "Home -1" → home team must win by more than 1
            handi_match = re.search(r"(Home|Away)\s*([-+]?\d+\.?\d*)", pred, re.IGNORECASE)
            if handi_match:
                side = handi_match.group(1).lower()
                handicap = float(handi_match.group(2))
                adjusted = (home_goals + handicap) if side == "home" else (away_goals + handicap)
                opponent = away_goals if side == "home" else home_goals
                return "won" if adjusted > opponent else "lost"

    except Exception as e:
        logger.warning(f"Status resolution failed for score={score}, market={market}: {e}")

    return "pending"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class FootballPredictionAgent:
    """
    Autonomous agent that generates structured football predictions
    by conducting multi-step web research and returning fully nested dicts.
    """

    def __init__(self, model: str = "qwen2.5:7b", ollama_base_url: str = "http://localhost:11434"):
        self.llm = OllamaLLM(model=model, base_url=ollama_base_url)

        self.registry = ToolRegistry()
        self.registry.register(WebSearchTool())
        self.registry.register(CalculatorTool())

        self.planner = Planner(self.llm, self.registry.list_all())
        self.reflector = Reflector(self.llm)
        self.synthesizer = Synthesizer(self.llm)

        TRAJECTORY_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Public: single match
    # ------------------------------------------------------------------

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

        # Build market keyword for Step 5 searches
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
            market=market,
            market_keyword=market_keyword,
            match_status=match_status,
            score=score,
            status_instruction=status_instruction,
        )

        # --- Agent loop ---
        state       = AgentState(task=task)
        scratchpad  = Scratchpad()
        trajectory  = []

        logger.info(f"Predicting: {home_team} vs {away_team} ({league})")

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

        # --- Synthesize raw analysis ---
        raw_analysis = self.synthesizer.compile(state)
        state.final_answer = raw_analysis

        # --- Structure into nested dict ---
        structured = self._structure_prediction(raw_analysis, match_data)

        # --- Resolve finished match status from actual score ---
        if match_status == "Finished":
            structured["status"] = resolve_match_status(
                structured.get("prediction", ""),
                market,
                score,
            )

        self._save_trajectory(task, trajectory, structured)
        return structured

    # ------------------------------------------------------------------
    # Public: full daily payload
    # ------------------------------------------------------------------

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
                logger.info(f"skipping match: {match.get("id")}")
                continue
            logger.info(f"\n[{idx}/{total}] {match.get('homeTeam')} vs {match.get('awayTeam')}")
            result = self.predict_match(match)
            results.append(result)

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
            "basic":         sum(1 for m in results if m.get("type") == "basic"),
            "premium":       sum(1 for m in results if m.get("type") == "premium"),
            "super_premium": sum(1 for m in results if m.get("type") == "super-premium"),
            "tip_of_the_day": tip_label,
        }

        return {
            "date":         date,
            "generated_at": payload.get("fetched_at", ""),
            "total":        total,
            "summary":      summary,
            "matches":      results,
        }

    # ------------------------------------------------------------------
    # Private: JSON structuring
    # ------------------------------------------------------------------

    def _structure_prediction(self, raw_analysis: str, match_data: dict) -> dict:
        """
        Ask the LLM to convert free-text analysis into the structured JSON schema,
        then merge with the preserved original match fields.
        """
        home_team    = match_data.get("homeTeam", "Unknown")
        away_team    = match_data.get("awayTeam", "Unknown")
        league       = match_data.get("league", "Unknown")
        market       = match_data.get("markets", "Over 2.5 Goals")
        match_status = match_data.get("matchStatus", "Not Started")
        score        = match_data.get("score", "0-0")

        prompt = JSON_STRUCTURE_PROMPT.format(
            home_team=home_team,
            away_team=away_team,
            league=league,
            market=market,
            score=score,
            match_status=match_status,
            raw_analysis=raw_analysis,
        )

        logger.info("  Structuring analysis into JSON...")
        raw_json = self.llm.invoke(prompt)
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
            "markets":     market,
            # ── From LLM structured output ────────────────────────────
            **parsed,
        }

    def _parse_json(self, raw: str) -> dict:
        """
        Robustly extract a JSON object from LLM output.
        Strips markdown fences, finds the outermost { }, falls back to defaults.
        """
        # 1. Strip markdown code fences
        clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        # 2. Grab outermost JSON object
        brace_match = re.search(r"\{[\s\S]*\}", clean)
        if brace_match:
            clean = brace_match.group(0)

        # 3. Parse
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.warning(f"  JSON parse failed ({e}) — using safe defaults")
            return self._default_fields()

    @staticmethod
    def _default_fields() -> dict:
        """Safe fallback when the LLM fails to return valid JSON."""
        return {
            "prediction":              "N/A",
            "reason":                  "Insufficient data returned from research. Unable to generate a confident prediction.",
            "type":                    "basic",
            "status":                  "pending",
            "expected_score":          "N/A",
            "confidence_score":        0,
            "risk_level":              "High",
            "value_rating":            1,
            "tip_of_the_day":          False,
            "match_importance":        "Medium",
            "league_round":            "Unknown",
            "referee":                 None,
            "win_probabilities":       {"home": 34, "draw": 33, "away": 33},
            "expected_goals":          {"home": 1.0, "away": 1.0},
            "form":                    {"home": "UNKNOWN", "away": "UNKNOWN"},
            "h2h_summary": {
                "played":       0,
                "home_wins":    0,
                "draws":        0,
                "away_wins":    0,
                "avg_goals":    0.0,
                "last_meeting": "No data available",
            },
            "key_factors":             ["Research data unavailable."],
            "injury_alert": {
                "active":    False,
                "home_team": "Unknown",
                "away_team": "Unknown",
            },
            "basic_prediction":         None,
            "premium_prediction":       None,
            "super_premium_prediction": None,
            "alternative_tip":          None,
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