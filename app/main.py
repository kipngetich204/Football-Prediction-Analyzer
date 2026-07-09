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

import os

import requests


from agent.football_prediction_agent import FootballPredictionAgent



logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Firestore support is left here as an optional extension for the CLI runner.


# Snapshot helpers are kept as placeholders for future pipeline control.









# The main controller currently just runs the prediction flow.
def compute_hash(data: object) -> str:
    """Compute a stable SHA-256 hash of any JSON-serialisable object."""
    serialised = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()



# Pull the latest daily match data from the backend service.
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


# Load data from a file, stdin, or the live API.
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


# Run the prediction pipeline from the command line.
def main():
    logger.info("FOOTBALL PREDICTION ANALYZER — Agent-Based Web Research")

    payload = load_payload()

    total = payload.get("total", len(payload.get("matches", [])))
    logger.info(f"\n  Date    : {payload.get('date', 'Unknown')}")
    logger.info(f"  Matches : {total}")

    # The current flow does not need an extra gate before running.
    current_hash  = compute_hash(payload) if payload else None
   



    logger.info(f"\nController decision → just running ")


    logger.info(f"Pipeline RUNNING: skipped desicion")

    # Start the agent and generate the predictions.
    logger.info("\nStarting research agent...\n")
    try:
        agent = FootballPredictionAgent(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",
        )
    except ValueError as exc:
        logger.error(str(exc))
        return

    result = agent.predict_all_matches(payload)

    # No persistence step is currently used in this lightweight runner.
 

    # Save the generated output to a JSON file.
    output_path = Path(f"predictions_ testing_{result['date']}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"\n  Full JSON saved → {output_path}")

    # Firestore export is not used in this runner.
  

    logger.info("=" * 70)


if __name__ == "__main__":
    main()