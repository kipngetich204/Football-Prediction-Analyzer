# Football Prediction Analyzer

Football Prediction Analyzer is a Python project that runs an agent-based football prediction workflow. It combines web research, tool use, and an LLM to build structured match predictions for upcoming games.

The current implementation uses Groq through LangChain, with a research loop that plans tool calls, reflects on collected evidence, synthesizes a match analysis, and formats the final output into a structured prediction object.

## Features

- Runs a multi-step research agent for each match
- Uses tool-based web search and calculation helpers
- Produces structured predictions with confidence, risk, form, h2h data, injuries, and tiered betting insights
- Includes a GitHub Actions workflow for scheduled daily runs
- Supports optional Firestore export for storing results

## Project Structure

- agent/ — planning, reflection, synthesis, and main prediction agent logic
- app/ — CLI entry points for running predictions
- tools/ — reusable tools such as web search and calculation helpers
- memory/ — scratchpad state used during agent execution
- .github/workflows/ — automation for scheduled runs

## Requirements

- Python 3.11+
- A Groq API key
- Optional Firebase credentials if Firestore export is enabled

## Setup

1. Clone the repository
2. Create and activate a virtual environment
3. Install the dependencies

```bash
python -m venv .fpa_env
source .fpa_env/bin/activate  # Linux/macOS
.fpa_env\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Environment Variables

Create a .env file or export these variables before running the app:

```bash
GROQ_API_KEY=your_groq_api_key
```

If you want to use the Firestore export path, also provide:

```bash
FIREBASE_PROJECT_ID=...
FIREBASE_PRIVATE_KEY_ID=...
FIREBASE_PRIVATE_KEY=...
FIREBASE_CLIENT_EMAIL=...
FIREBASE_CLIENT_ID=...
FIREBASE_CLIENT_CERT_URL=...
```

## Running the App

Run the main prediction entry point:

```bash
python -m app.football_main
```

The app will fetch the latest daily match data, run the prediction workflow, and output the results through the configured pipeline.

## GitHub Actions

A scheduled workflow is included in [.github/workflows/daily_predictions.yml](.github/workflows/daily_predictions.yml). It runs daily and can also be triggered manually.

You will need to add these repository secrets:

- GROQ_API_KEY
- FIREBASE_CREDS

## Notes

- The agent relies on a working Groq API key to generate predictions.
- The workflow uploads the trajectories directory as an artifact for inspection after each run.
- If you want to extend the project, the most natural places to add features are the agent logic in the agent/ folder and the tool implementations in tools/.
