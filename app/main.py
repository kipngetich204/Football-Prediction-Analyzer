"""
Football Prediction — CLI Runner
Accepts a full daily matches JSON payload and outputs structured nested predictions.
Usage:
  python main.py                        # uses built-in sample payload
  python main.py payload.json           # reads payload from file
  cat payload.json | python main.py     # reads payload from stdin
"""
import hashlib
import json
import logging
import sys
from pathlib import Path

import requests

from agent.football_prediction_agent import FootballPredictionAgent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------
SNAPSHOT_FILE = Path(__file__).parent / ".snapshot_state.json"


def load_previous_hash() -> str | None:
    """Return the previously stored hash, or None if none exists."""
    if not SNAPSHOT_FILE.exists():
        return None
    try:
        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            return json.load(f).get("last_hash")
    except (json.JSONDecodeError, OSError):
        return None


def save_current_hash(hash_value: str) -> None:
    """Persist the current hash for the next run to compare against."""
    try:
        with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_hash": hash_value}, f)
    except OSError as e:
        logger.error(f"Could not save snapshot state: {e}")


# ---------------------------------------------------------------------------
# Pipeline controller
# ---------------------------------------------------------------------------
def compute_hash(data: object) -> str:
    """Compute a stable SHA-256 hash of any JSON-serialisable object."""
    serialised = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def should_run_pipeline(
    current_fetched_data: object,
    previous_snapshot_hash: str | None,
    current_snapshot_hash: str | None,
) -> dict:
    """
    Decide whether the prediction pipeline should run.

    DECISION RULES:
      1. Empty / invalid data            → SKIP
      2. current_snapshot_hash missing   → SKIP
      3. previous_snapshot_hash missing  → RUN  (first run)
      4. Hashes differ                   → RUN  (new data)
      5. Hashes equal                    → SKIP (no change)
      6. Uncertain (catch-all)           → SKIP (safety first)

    Returns ONLY valid JSON-serialisable dict:
      { "shouldRun": bool, "reason": str, "action": "run" | "skip" }
    """
    def _skip(reason: str) -> dict:
        return {"shouldRun": False, "reason": reason, "action": "skip"}

    def _run(reason: str) -> dict:
        return {"shouldRun": True, "reason": reason, "action": "run"}

    # Rule 1 — empty or invalid data
    if not current_fetched_data:
        return _skip("Data is empty or invalid")
    if not isinstance(current_fetched_data, dict):
        return _skip("Data is not a valid JSON object")
    if not isinstance(current_fetched_data.get("matches", []), list):
        return _skip("Data contains an invalid matches field")

    # Rule 2 — current hash missing
    if not current_snapshot_hash:
        return _skip("current_snapshot_hash is missing; cannot compare safely")

    # Rule 3 — no previous hash → first run
    if not previous_snapshot_hash:
        return _run("No previous snapshot hash found; running for the first time")

    # Rules 4 & 5 — hash comparison
    if current_snapshot_hash != previous_snapshot_hash:
        return _run("Snapshot hash changed; new data detected")

    if current_snapshot_hash == previous_snapshot_hash:
        return _skip("Snapshot hash unchanged; data has not changed")

    # Rule 6 — catch-all safety net
    return _skip("Uncertain state; skipping as a precaution")


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def get_daily_matches() -> dict | None:
    """Synchronous fetch from the backend API."""
    try:
        logger.info("Fetching daily matches from API...")
        response = requests.get("https://backend-livetips.onrender.com/daily", timeout=200)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        logger.warning(f"Could not fetch from API ({e})")
    return None


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def load_payload() -> dict:
    """
    Load match payload from:
      1. File path passed as sys.argv[1]
      2. Stdin pipe
      3. Live API call
    """
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            logger.error(f"ERROR: File not found: {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        logger.info(f"Loaded payload from file: {path}")
        return payload

    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
            logger.info("Loaded payload from stdin")
            return payload
        except json.JSONDecodeError as e:
            logger.error(f"ERROR: Invalid JSON from stdin: {e}")
            sys.exit(1)

    logger.info("No payload provided — fetching from live API.")
    data = get_daily_matches()
    return data if data else {}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    logger.info("FOOTBALL PREDICTION ANALYZER — Agent-Based Web Research")

    payload = load_payload()

    total = payload.get("total", len(payload.get("matches", [])))
    logger.info(f"\n  Date    : {payload.get('date', 'Unknown')}")
    logger.info(f"  Matches : {total}")

    # ── Controller gate ────────────────────────────────────────────────────
    current_hash  = compute_hash(payload) if payload else None
    previous_hash = load_previous_hash()

    decision = should_run_pipeline(
        current_fetched_data=payload,
        previous_snapshot_hash=previous_hash,
        current_snapshot_hash=current_hash,
    )

    logger.info(f"\nController decision → {json.dumps(decision)}")

    if not decision["shouldRun"]:
        logger.info(f"Pipeline SKIPPED: {decision['reason']}")
        return

    logger.info(f"Pipeline RUNNING: {decision['reason']}")

    # ── Run agent ──────────────────────────────────────────────────────────
    logger.info("\nStarting research agent...\n")
    agent  = FootballPredictionAgent(model="qwen2.5:7b")
    result = agent.predict_all_matches(payload)

    # ── Persist hash after successful run ──────────────────────────────────
    if current_hash:
        save_current_hash(current_hash)

    # ── Save output ────────────────────────────────────────────────────────
    output_path = Path(f"predictions_{result['date']}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"\n  Full JSON saved → {output_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()